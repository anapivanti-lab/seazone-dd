"""CND Estadual do Mato Grosso do Sul (SEFAZ-MS). UF = MS.
Tem captcha de imagem: seleciona CNPJ e preenche; você digita o captcha e emite."""
from ..base import BaseProvider, registrar

URL = "https://servicos.efazenda.ms.gov.br/pndfis/home/emissao"


@registrar
class SefazMS(BaseProvider):
    nome = "CND Estadual (Fazenda) — MS"
    nome_arquivo = "CND_Estadual_MS"
    ufs = ["MS"]

    async def abrir(self, ctx, page):
        await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(1500)
        try:
            await page.select_option("#Tipo", label="CNPJ")
        except Exception:
            pass
        try:
            await page.fill("#Numero", ctx.documento, timeout=6000)
        except Exception:
            pass
