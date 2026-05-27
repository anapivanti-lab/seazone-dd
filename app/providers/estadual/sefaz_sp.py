"""CND Estadual de São Paulo (SEFAZ-SP). UF = SP.
Tem captcha: abre, marca CNPJ e preenche o número. Você resolve o captcha."""
from ..base import BaseProvider, registrar

URL = "https://www10.fazenda.sp.gov.br/CertidaoNegativaDeb/Pages/EmissaoCertidaoNegativa.aspx"


@registrar
class SefazSP(BaseProvider):
    nome = "CND Estadual (Fazenda) — SP"
    nome_arquivo = "CND_Estadual_SP"
    ufs = ["SP"]

    async def abrir(self, ctx, page):
        await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(1200)
        try:
            await page.check("#MainContent_cnpjradio")
            await page.wait_for_timeout(400)
        except Exception:
            pass
        try:
            await page.fill("#MainContent_txtDocumento", ctx.documento, timeout=8000)
        except Exception:
            pass
