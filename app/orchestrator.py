"""Orquestra a DD: monta a checklist completa e processa cada item conforme o
modo (auto / abrir / manual). Tudo é organizado numa pasta por franquia."""
from __future__ import annotations

import asyncio
import os
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

from .busca_municipal import google_url as _google_municipal
from .checklist import itens_para
from .cnpj_dados import consultar as consultar_cnpj
from .config import CERT_ORIGINS, CERT_PFX, CERT_SENHA, PASTA_PERFIL
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
    sob_demanda: bool = False   # tem botão "Abrir site" (abre só quando você clica)


@dataclass
class Job:
    id: str
    ctx: Contexto
    selecionados: list[str] = field(default_factory=list)
    passos: list[Passo] = field(default_factory=list)
    processos: list = field(default_factory=list)  # resumos de processos lidos
    cnpj_dados: dict = field(default_factory=dict)  # dados da BrasilAPI (CNAE, situação, sócios)
    estado: str = "criado"  # criado | executando | aguardando_voce | concluido
    criado_em: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    _pw: object = field(default=None, repr=False, compare=False)
    _contexto: object = field(default=None, repr=False, compare=False)
    _lock: object = field(default=None, repr=False, compare=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "estado": self.estado, "tipo": self.ctx.tipo.value,
            "documento": self.ctx.documento, "nome": self.ctx.nome,
            "uf": self.ctx.uf, "municipio": self.ctx.municipio,
            "pasta": str(self.ctx.pasta_saida),
            "passos": [
                {"nome": p.nome, "grupo": p.grupo, "modo": p.modo,
                 "status": p.status, "mensagem": p.mensagem, "arquivo": p.arquivo,
                 "sob_demanda": p.sob_demanda}
                for p in self.passos
            ],
            "processos": self.processos,
            "cnpj_dados": self.cnpj_dados,
        }


JOBS: dict[str, Job] = {}


def criar_job(ctx: Contexto, selecionados: list[str] | None = None,
              municipal_url: str = "") -> Job:
    selecionados = selecionados or []
    dados = consultar_cnpj(ctx.documento)  # dados grátis do CNPJ (CNAE, situação, sócios, endereço)
    if dados:
        if not ctx.nome and dados.get("razao_social"):
            ctx.nome = dados["razao_social"]
        if not ctx.endereco and dados.get("endereco"):
            ctx.endereco = dados["endereco"]
    ctx.pasta_saida = preparar_pasta(ctx)
    passos = []
    for it in itens_para(ctx):
        sob_demanda = False
        if it.modo == "manual":
            status, msg = "manual", (it.obs or "Obtenha o documento e suba o PDF aqui.")
        elif it.modo == "local":
            status, msg = "local", (it.obs or "Preencha a UF/cidade no topo.")
        elif it.modo == "abrir":
            sob_demanda = True
            status, msg = "aguardando", "Clique em 'Abrir site' para abrir no seu navegador."
        elif it.modo == "auto":
            prov = provedor_por_nome(it.provider)
            if prov and getattr(prov, "auto_completo", False):
                # 100% automático (headless): roda sozinho ao iniciar, sem abrir aba
                status, msg = "aguardando", "Automático — emitido ao iniciar (sem captcha)."
            else:
                sob_demanda = True
                base = "Clique em 'Abrir site' para abrir e preencher."
                status, msg = "aguardando", (f"{it.obs} {base}" if it.obs else base)
        else:
            status, msg = "aguardando", ""
        passos.append(Passo(nome=it.nome, grupo=it.grupo, modo=it.modo, url=it.url,
                            provider=it.provider, status=status, mensagem=msg,
                            sob_demanda=sob_demanda))
    # CND Municipal de cidade não cadastrada: aponta para o site achado na busca
    # (ou para a busca do Google já pronta), virando um item "abrir" com botão.
    muni = next((p for p in passos if p.grupo == "Municipais"), None)
    if muni and muni.modo in ("manual", "local") and ctx.municipio:
        url = municipal_url or _google_municipal(ctx.municipio, ctx.uf)
        muni.modo, muni.url, muni.sob_demanda, muni.status = "abrir", url, True, "aguardando"
        muni.mensagem = (
            "Achei o site da CND Municipal — clique em 'Abrir site' e baixe o PDF."
            if municipal_url else
            "Não achei o link exato — abre a busca do Google pronta; clique no site da prefeitura."
        )

    job = Job(id=uuid.uuid4().hex[:8], ctx=ctx, selecionados=selecionados, passos=passos)
    job.cnpj_dados = dados or {}
    job._lock = asyncio.Lock()  # serializa a abertura do navegador (evita corrida)
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
    # Apresenta o certificado digital automaticamente nos sites que pedem login
    if CERT_PFX and Path(CERT_PFX).exists():
        comum["client_certificates"] = [
            {"origin": o, "pfxPath": CERT_PFX, "passphrase": CERT_SENHA} for o in CERT_ORIGINS
        ]
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
            passo.mensagem = (f"✅ PDF salvo na PASTA da franquia: {Path(arq).name} "
                              "— use o botão 'Abrir PDF' aqui do lado. (O arquivo que cai no "
                              "Downloads com nome estranho é lixo do Chrome; pode ignorar.)")
        except Exception as e:
            passo.mensagem = f"Baixou, mas falhou ao salvar: {e}"

    page.on("download", lambda d: asyncio.ensure_future(salvar(d)))
    # captura também downloads que abrem em aba/janela nova (ex.: TST)
    page.on("popup", lambda p: p.on("download", lambda d: asyncio.ensure_future(salvar(d))))


async def executar_job(job: Job) -> None:
    """Ao iniciar, roda APENAS os 100% automáticos (headless, sem abrir abas).
    Os que precisam de você (captcha/login) ficam com botão 'Abrir site' e só
    abrem quando você clica — um de cada vez, na mesma janela."""
    job.estado = "executando"
    full = [
        (p, provedor_por_nome(p.provider)) for p in job.passos
        if p.modo == "auto" and (not job.selecionados or p.nome in job.selecionados)
    ]
    full = [(p, prov) for p, prov in full if prov and getattr(prov, "auto_completo", False)]

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

    job.estado = "aguardando_voce"


async def _descartar_navegador(job: Job) -> None:
    """Fecha/limpa o navegador controlado (ex.: você fechou a janela)."""
    try:
        if job._contexto is not None:
            await job._contexto.close()
    except Exception:
        pass
    try:
        if job._pw is not None:
            await job._pw.stop()
    except Exception:
        pass
    job._contexto = None
    job._pw = None


async def _garantir_navegador(job: Job):
    """Abre o navegador controlado UMA vez e reusa para todas as certidões
    (assim elas viram abas na MESMA janela, não janelas novas)."""
    if job._contexto is None:
        job._pw = await async_playwright().start()
        job._contexto = await _abrir_navegador(job._pw)
    return job._contexto


async def abrir_item(job: Job, nome: str) -> Passo | None:
    """Abre/emite UM item específico (chamado pelo botão 'Abrir site')."""
    passo = next((p for p in job.passos if p.nome == nome), None)
    if passo is None:
        return None

    # 'abrir': sites com bloqueio anti-robô -> vão para o SEU navegador normal.
    if passo.modo == "abrir":
        _copiar_clipboard(job.ctx.documento)
        try:
            if passo.url:
                os.startfile(passo.url)
            passo.status = "aberta"
            passo.mensagem = ("Abri no seu navegador. Cole o CNPJ/CPF com Ctrl+V, valide o captcha, "
                              "baixe o PDF e clique em 'Enviar PDF' aqui.")
        except Exception as e:
            passo.status = "erro"
            passo.mensagem = f"Não consegui abrir a página: {e}"
        return passo

    if passo.modo == "auto":
        prov = provedor_por_nome(passo.provider)
        if prov is None:
            passo.status = "erro"
            passo.mensagem = "Provedor automático não encontrado."
            return passo
        # 100% automático: roda headless na hora (sem abrir aba)
        if getattr(prov, "auto_completo", False):
            pwf = await async_playwright().start()
            try:
                nav = await pwf.chromium.launch(headless=True)
                ctxf = await nav.new_context(accept_downloads=True)
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
                finally:
                    await page.close()
                    await ctxf.close()
                    await nav.close()
            finally:
                await pwf.stop()
            return passo
        # precisa de captcha: abre uma ABA na MESMA janela controlada e preenche.
        # O lock garante que só UMA certidão abre por vez (sem corrida no perfil).
        if job._lock is None:
            job._lock = asyncio.Lock()
        async with job._lock:
            for tentativa in range(2):
                try:
                    contexto = await _garantir_navegador(job)
                    page = await contexto.new_page()
                    _ligar_captura(page, prov, passo, job.ctx)
                    await prov.abrir(job.ctx, page)
                    passo.status = "aberta"
                    passo.mensagem = "Aba aberta — resolva o captcha e emita; o PDF é salvo sozinho."
                    return passo
                except Exception as e:
                    nome_err = type(e).__name__
                    fechado = "TargetClosed" in nome_err or "closed" in str(e).lower()
                    if fechado and tentativa == 0:
                        # a janela foi fechada -> descarta e recria UMA vez
                        await _descartar_navegador(job)
                        continue
                    passo.status = "erro"
                    passo.mensagem = (
                        "A janela foi fechada; abri uma nova — clique em 'Reabrir site'."
                        if fechado else f"Não consegui abrir o site ({nome_err})."
                    )
                    return passo
        return passo

    return passo


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
