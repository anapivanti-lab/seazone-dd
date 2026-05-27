"""Orquestra a emissão: abre UM navegador 'disfarçado' de Chrome normal e
prepara cada certidão em uma aba, deixando você concluir os captchas no seu
tempo. Qualquer PDF que algum site baixar é capturado e salvo automaticamente.
"""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from playwright.async_api import async_playwright

from .config import PASTA_PERFIL
from .models import Contexto
from .providers import provedores_para
from .providers.util import salvar_download
from .storage import preparar_pasta, salvar_relatorio


@dataclass
class Passo:
    nome: str
    status: str = "aguardando"   # aguardando | aberta | sucesso | pendente_captcha | erro
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
                {"nome": p.nome, "status": p.status, "mensagem": p.mensagem, "arquivo": p.arquivo}
                for p in self.passos
            ],
        }


# Jobs em memória (somem quando o servidor reinicia — suficiente por enquanto).
JOBS: dict[str, Job] = {}


def _selecao(ctx: Contexto, nomes: list[str]):
    provs = provedores_para(ctx)
    if nomes:
        provs = [p for p in provs if p.nome in nomes]
    return provs


def criar_job(ctx: Contexto, selecionados: list[str] | None = None) -> Job:
    selecionados = selecionados or []
    ctx.pasta_saida = preparar_pasta(ctx)
    provs = _selecao(ctx, selecionados)
    job = Job(
        id=uuid.uuid4().hex[:8],
        ctx=ctx,
        selecionados=selecionados,
        passos=[Passo(nome=p.nome) for p in provs],
    )
    JOBS[job.id] = job
    return job


async def _abrir_navegador(pw):
    """Abre o Chrome 'disfarçado' (sem cara de robô) com perfil persistente."""
    comum = dict(
        user_data_dir=str(PASTA_PERFIL),
        headless=False,
        accept_downloads=True,
        args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
        ignore_default_args=["--enable-automation"],
        locale="pt-BR",
        no_viewport=True,
    )
    try:
        contexto = await pw.chromium.launch_persistent_context(channel="chrome", **comum)
    except Exception:
        # Sem o Chrome instalado, usa o Chromium que vem junto.
        contexto = await pw.chromium.launch_persistent_context(**comum)
    await contexto.add_init_script(
        "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
    )
    return contexto


def _ligar_captura(page, prov, passo, ctx):
    """Salva automaticamente qualquer PDF que esta aba baixar."""

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
    provs = _selecao(job.ctx, job.selecionados)
    pw = await async_playwright().start()
    job._pw = pw
    try:
        contexto = await _abrir_navegador(pw)
    except Exception as e:
        for p in job.passos:
            p.status = "erro"
            p.mensagem = f"Não consegui abrir o navegador: {e}"
        job.estado = "concluido"
        await pw.stop()
        return
    job._contexto = contexto

    for passo, prov in zip(job.passos, provs):
        try:
            page = await contexto.new_page()
            _ligar_captura(page, prov, passo, job.ctx)
            await prov.abrir(job.ctx, page)
            passo.status = "aberta"
            passo.mensagem = "Aba aberta e preenchida — resolva o captcha e clique em emitir."
        except Exception as e:
            passo.status = "erro"
            passo.mensagem = f"Não consegui abrir o site ({type(e).__name__})."

    job.estado = "aguardando_voce"


async def concluir_job(job: Job) -> None:
    """Fecha o navegador e gera o relatório final."""
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
            p.status = "pendente_captcha"
            if not p.mensagem:
                p.mensagem = "Não emitida nesta sessão."
    job.estado = "concluido"
    salvar_relatorio(job)
