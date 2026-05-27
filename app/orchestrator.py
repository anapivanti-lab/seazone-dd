"""Orquestra a emissão: abre o navegador e percorre os provedores um a um."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from playwright.async_api import async_playwright

from .config import NAVEGADOR_VISIVEL
from .models import Contexto, Status
from .providers import provedores_para
from .storage import preparar_pasta, salvar_relatorio


@dataclass
class Passo:
    nome: str
    status: str = "aguardando"
    mensagem: str = ""
    arquivo: str | None = None


@dataclass
class Job:
    id: str
    ctx: Contexto
    passos: list[Passo] = field(default_factory=list)
    estado: str = "criado"  # criado | executando | concluido
    criado_em: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

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
            "passos": [vars(p) for p in self.passos],
        }


# Guarda os jobs em memória (some quando o servidor reinicia — suficiente por enquanto).
JOBS: dict[str, Job] = {}


def criar_job(ctx: Contexto) -> Job:
    ctx.pasta_saida = preparar_pasta(ctx)
    provs = provedores_para(ctx)
    job = Job(id=uuid.uuid4().hex[:8], ctx=ctx, passos=[Passo(nome=p.nome) for p in provs])
    JOBS[job.id] = job
    return job


async def executar_job(job: Job) -> None:
    job.estado = "executando"
    provs = provedores_para(job.ctx)
    async with async_playwright() as pw:
        navegador = await pw.chromium.launch(headless=not NAVEGADOR_VISIVEL)
        contexto = await navegador.new_context(accept_downloads=True)
        for passo, prov in zip(job.passos, provs):
            passo.status = "executando"
            page = await contexto.new_page()
            try:
                res = await prov.emitir(job.ctx, page)
                passo.status = res.status.value
                passo.mensagem = res.mensagem
                passo.arquivo = str(res.arquivo) if res.arquivo else None
            except Exception as e:
                passo.status = Status.ERRO.value
                passo.mensagem = f"Erro inesperado: {e}"
            finally:
                await page.close()
        await contexto.close()
        await navegador.close()
    job.estado = "concluido"
    salvar_relatorio(job)
