"""CND Estadual de Santa Catarina (SEFAZ-SC). UF = SC.
Tem captcha, então: abre, escolhe tipo CNPJ e preenche o número. Você só
resolve o captcha e emite."""
from ..base import BaseProvider, registrar

URL = "https://sat.sef.sc.gov.br/tax.NET/Sat.CtaCte.Web/SolicitacaoCnd.aspx"


@registrar
class SefazSC(BaseProvider):
    nome = "CND Estadual (Fazenda) — SC"
    nome_arquivo = "CND_Estadual_SC"
    ufs = ["SC"]

    async def abrir(self, ctx, page):
        await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(1500)
        try:
            await page.select_option(
                "#Body_Main_Main_sepBusca_idnCnd_IdentificationTypeField", label="CNPJ")
            await page.wait_for_timeout(500)
        except Exception:
            pass
        try:
            await page.fill("#Body_Main_Main_sepBusca_idnCnd_MaskedField", ctx.documento, timeout=8000)
        except Exception:
            pass
