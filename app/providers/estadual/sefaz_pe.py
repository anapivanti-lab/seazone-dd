"""CND Estadual de Pernambuco (SEFAZ-PE). UF = PE. SEM captcha.
Seleciona CNPJ, preenche e localiza. Você confere e clica em Emitir."""
from ..base import BaseProvider, registrar

URL = "https://efisco.sefaz.pe.gov.br/sfi_trb_gcc/PREmitirCertidaoRegularidadeFiscalMovel"


@registrar
class SefazPE(BaseProvider):
    nome = "CND Estadual (Fazenda) — PE"
    nome_arquivo = "CND_Estadual_PE"
    ufs = ["PE"]

    async def abrir(self, ctx, page):
        await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(1500)
        try:
            await page.select_option("#tpDocumentoIdentificacaoCertidaoRegularidade", label="CNPJ")
        except Exception:
            pass
        try:
            await page.fill("#NuDocumentoIdentificacaoCertidaoRegularidade", ctx.documento, timeout=6000)
        except Exception:
            pass
        try:
            await page.click("#btt_localizar", timeout=5000)
        except Exception:
            pass
