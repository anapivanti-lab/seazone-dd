"""CND Federal — Receita Federal + PGFN. PJ e PF.

Fluxo: abre a página, clica em "Pessoa Jurídica" (ou "Pessoa Física") e
preenche o documento no campo 'niContribuinte'. Você só resolve o captcha e emite.
"""
from ..base import BaseProvider, registrar
from ...models import TipoPessoa

URL = "https://servicos.receitafederal.gov.br/servico/certidoes/"


@registrar
class CNDFederal(BaseProvider):
    nome = "CND Federal (Receita/PGFN)"
    nome_arquivo = "CND_Federal"

    async def abrir(self, ctx, page):
        await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)
        alvo = "Pessoa Jurídica" if ctx.tipo == TipoPessoa.PJ else "Pessoa Física"
        try:
            await page.click(f"text={alvo}", timeout=8000)
            await page.wait_for_timeout(1500)
        except Exception:
            pass
        try:
            await page.fill("input[name='niContribuinte']", ctx.documento, timeout=8000)
        except Exception:
            pass
