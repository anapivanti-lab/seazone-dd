"""Orquestra a DD: monta a checklist completa, abre em abas as certidões que
têm automação (deixando você concluir os captchas no seu ritmo) e organiza tudo
numa pasta por franquia. Os documentos sem automação você sobe manualmente."""
from __future__ import annotations

import asyncio
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
    auto: bool = False
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
            "id": self.id,
            "estado": self.estado,
            "tipo": self.ctx.tipo.value,
            "documento": self.ctx.documento,
            "nome": self.ctx.nome,
            "uf": self.ctx.uf,
            "municipio": self.ctx.municipio,
            "pasta": str(self.ctx.pasta_saida),
            "passos": [
                {
                    "nome": p.nome, "grupo": p.grupo, "auto": p.auto,
                    "status": p.status, "mensagem": p.mensagem, "arquivo": p.arquivo,
                }
                for p in self.passos
            ],
        }


JOBS: dict[str, Job] = {}


def criar_job(ctx: Contexto, selecionados: list[str] | None = None) -> Job:
    selecionados = selecionados or []
    ctx.pasta_saida = preparar_pasta(ctx)
    passos = []
    for it in itens_para(ctx):
        auto = it.provider is not None and provedor_por_nome(it.provider) is not None
        passos.append(
            Passo(
                nome=it.nome, grupo=it.grupo, auto=auto,
                status="aguardando" if auto else "manual",
                mensagem="" if auto else "Obtenha o documento e suba o PDF aqui.",
            )
        )
    job = Job(id=uuid.uuid4().hex[:8], ctx=ctx, selecionados=selecionados, passos=passos)
    JOBS[job.id] = job
    return job


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
        "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
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
    abrir = [
        p for p in job.passos
        if p.auto and (not job.selecionados or p.nome in job.selecionados)
    ]
    if not abrir:
        job.estado = "aguardando_voce"  # só uploads manuais nesta sessão
        return

    pw = await async_playwright().start()
    job._pw = pw
    try:
        contexto = await _abrir_navegador(pw)
    except Exception as e:
        for p in abrir:
            p.status = "erro"
            p.mensagem = f"Não consegui abrir o navegador: {e}"
        job.estado = "aguardando_voce"
        await pw.stop()
        return
    job._contexto = contexto

    for passo in abrir:
        prov = provedor_por_nome(passo.nome)
        try:
            page = await contexto.new_page()
            _ligar_captura(page, prov, passo, job.ctx)
            await prov.abrir(job.ctx, page)
            passo.status = "aberta"
            passo.mensagem = "Aba aberta — conclua no site (captcha + emitir)."
        except Exception as e:
            passo.status = "erro"
            passo.mensagem = f"Não consegui abrir o site ({type(e).__name__})."

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
