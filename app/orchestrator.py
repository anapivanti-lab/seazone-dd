"""Orquestra a DD: monta a checklist completa e processa cada item conforme o
modo (auto / abrir / manual). Tudo é organizado numa pasta por franquia."""
from __future__ import annotations

import asyncio
import os
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from playwright.async_api import async_playwright

from .checklist import itens_para
from .config import PASTA_PERFIL
from .models import Contexto
from .providers.base import provedor_por_nome
from .providers.util import salvar_download
from .storage import preparar_pasta, salvar_relatorio


@dataclass
class Passo:
    nome: str
    grupo: str = ""
    modo: str = "manual"        # auto | abrir | manual
    url: str | None = None
    provider: str | None = None
    status: str = "aguardando"  # aguardando|aberta|sucesso|enviado|manual|pendente|erro
    mensagem: str = ""
    arquivo: str | None = None


@dataclass
class Job:
    id: str
    ctx: Contexto
    selecionados: list[str] = field(default_factory=list)
    passos: list[Passo] = field(default_factory=list)
    estado: str = "criado"  # criado | executando | aguardando_voce | concluido
    criado_em: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    _pw: object = field(default=None, repr=False, compare=False)
    _contexto: object = field(default=None, repr=False, compare=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "estado": self.estado, "tipo": self.ctx.tipo.value,
            "documento": self.ctx.documento, "nome": self.ctx.nome,
            "uf": self.ctx.uf, "municipio": self.ctx.municipio,
            "pasta": str(self.ctx.pasta_saida),
            "passos": [
                {"nome": p.nome, "grupo": p.grupo, "modo": p.modo,
                 "status": p.status, "mensagem": p.mensagem, "arquivo": p.arquivo}
                for p in self.passos
            ],
        }


JOBS: dict[str, Job] = {}


def criar_job(ctx: Contexto, selecionados: list[str] | None = None) -> Job:
    selecionados = selecionados or []
    ctx.pasta_saida = preparar_pasta(ctx)
    passos = []
    for it in itens_para(ctx):
        if it.modo == "manual":
            status, msg = "manual", (it.obs or "Obtenha o documento e suba o PDF aqui.")
        elif it.modo == "local":
            status, msg = "local", (it.obs or "Preencha a UF/cidade no topo.")
        else:
            status, msg = "aguardando", ""
        passos.append(Passo(nome=it.nome, grupo=it.grupo, modo=it.modo, url=it.url,
                            provider=it.provider, status=status, mensagem=msg))
    job = Job(id=uuid.uuid4().hex[:8], ctx=ctx, selecionados=selecionados, passos=passos)
    JOBS[job.id] = job
    return job


def _copiar_clipboard(texto: str) -> None:
    try:
        subprocess.run("clip", input=texto, text=True, shell=True, timeout=5)
    except Exception:
        pass


async def _abrir_navegador(pw):
    comum = dict(
        user_data_dir=str(PASTA_PERFIL), headless=False, accept_downloads=True,
        args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
        ignore_default_args=["--enable-automation"], locale="pt-BR", no_viewport=True,
    )
    try:
        contexto = await pw.chromium.launch_persistent_context(channel="chrome", **comum)
    except Exception:
        contexto = await pw.chromium.launch_persistent_context(**comum)
    await contexto.add_init_script(
        """
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'languages', {get: () => ['pt-BR','pt','en-US','en']});
        Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
        window.chrome = window.chrome || { runtime: {} };
        const _q = navigator.permissions && navigator.permissions.query;
        if (_q) navigator.permissions.query = (p) =>
          (p && p.name === 'notifications')
            ? Promise.resolve({ state: Notification.permission })
            : _q(p);
        """
    )
    return contexto


def _ligar_captura(page, prov, passo, ctx):
    async def salvar(download):
        try:
            arq = await salvar_download(download, ctx, prov.nome_arquivo)
            passo.status = "sucesso"
            passo.arquivo = str(arq)
            passo.mensagem = "PDF salvo automaticamente."
        except Exception as e:
            passo.mensagem = f"Baixou, mas falhou ao salvar: {e}"

    page.on("download", lambda d: asyncio.ensure_future(salvar(d)))


async def executar_job(job: Job) -> None:
    job.estado = "executando"
    abrir_items = [p for p in job.passos if p.modo == "abrir"]
    auto_items = [
        p for p in job.passos
        if p.modo == "auto" and (not job.selecionados or p.nome in job.selecionados)
    ]

    # 1) "Abrir no navegador normal": sem detecção de robô; copia o documento.
    if abrir_items:
        _copiar_clipboard(job.ctx.documento)
        ja_aberto = set()
        for passo in abrir_items:
            try:
                if passo.url and passo.url not in ja_aberto:
                    os.startfile(passo.url)  # abre no navegador padrão (Windows)
                    ja_aberto.add(passo.url)
                    passo.mensagem = ("Abri no seu navegador. Cole o CNPJ/CPF com Ctrl+V, valide o captcha, "
                                      "baixe o PDF e clique em 'Enviar PDF' aqui.")
                else:
                    passo.mensagem = ("Mesma página já aberta — uma certidão pode cobrir mais de um item. "
                                      "Baixe e suba o PDF aqui.")
                passo.status = "aberta"
            except Exception as e:
                passo.status = "erro"
                passo.mensagem = f"Não consegui abrir a página: {e}"

    # 2) "Automático": separa os 100% automáticos (headless, sem você precisar
    #    fazer nada) dos que precisam que você resolva o captcha (navegador visível).
    if auto_items:
        full, headed = [], []
        for passo in auto_items:
            prov = provedor_por_nome(passo.provider)
            if prov is None:
                passo.status = "erro"
                passo.mensagem = "Provedor automático não encontrado."
            elif getattr(prov, "auto_completo", False):
                full.append((passo, prov))
            else:
                headed.append((passo, prov))

        # 2a) 100% automáticos (headless): preenche, emite e salva o PDF sozinho
        if full:
            pwf = await async_playwright().start()
            try:
                nav = await pwf.chromium.launch(headless=True)
                ctxf = await nav.new_context(accept_downloads=True)
                for passo, prov in full:
                    page = await ctxf.new_page()
                    try:
                        arq = await prov.executar(job.ctx, page)
                        if arq:
                            passo.status = "sucesso"
                            passo.arquivo = str(arq)
                            passo.mensagem = "Baixado automaticamente (sem captcha)."
                        else:
                            passo.status = "erro"
                            passo.mensagem = "Não consegui capturar o PDF."
                    except Exception as e:
                        passo.status = "erro"
                        passo.mensagem = f"Falha na emissão automática ({type(e).__name__})."
                    finally:
                        await page.close()
                await ctxf.close()
                await nav.close()
            finally:
                await pwf.stop()

        # 2b) Precisam de captcha: navegador visível; você conclui
        if headed:
            pw = await async_playwright().start()
            job._pw = pw
            try:
                contexto = await _abrir_navegador(pw)
                job._contexto = contexto
                for passo, prov in headed:
                    try:
                        page = await contexto.new_page()
                        _ligar_captura(page, prov, passo, job.ctx)
                        await prov.abrir(job.ctx, page)
                        passo.status = "aberta"
                        passo.mensagem = "Aba aberta — resolva o captcha e emita; o PDF é salvo sozinho."
                    except Exception as e:
                        passo.status = "erro"
                        passo.mensagem = f"Não consegui abrir o site ({type(e).__name__})."
            except Exception as e:
                for passo, prov in headed:
                    passo.status = "erro"
                    passo.mensagem = f"Não consegui abrir o navegador: {e}"
                try:
                    await pw.stop()
                except Exception:
                    pass

    job.estado = "aguardando_voce"


async def concluir_job(job: Job) -> None:
    try:
        if job._contexto:
            await job._contexto.close()
    except Exception:
        pass
    try:
        if job._pw:
            await job._pw.stop()
    except Exception:
        pass
    for p in job.passos:
        if p.status in ("aberta", "aguardando", "executando"):
            p.status = "pendente"
            if not p.mensagem:
                p.mensagem = "Não concluída nesta sessão."
    job.estado = "concluido"
    salvar_relatorio(job)
