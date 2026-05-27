"""CND Estadual do Rio Grande do Sul (SEFAZ-RS). UF = RS.
Preenche o CNPJ e marca o ALTCHA (captcha de prova de trabalho, que se resolve
sozinho). Você confere e clica em Solicitar/Enviar."""
from ..base import BaseProvider, registrar

URL = "https://www.sefaz.rs.gov.br/sat/CertidaoSitFiscalSolic.aspx"


@registrar
class SefazRS(BaseProvider):
    nome = "CND Estadual (Fazenda) — RS"
    nome_arquivo = "CND_Estadual_RS"
    ufs = ["RS"]

    async def abrir(self, ctx, page):
        await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(1500)
        for sel in ["#txtCnpj", "input[name='cnpj']", "input[name='campoCnpj']"]:
            try:
                await page.fill(sel, ctx.documento, timeout=5000)
                break
            except Exception:
                pass
        try:
            await page.click("[id^='altcha_checkbox'], altcha-widget input[type=checkbox]", timeout=3000)
        except Exception:
            pass
