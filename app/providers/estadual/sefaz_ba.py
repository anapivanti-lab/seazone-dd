"""CND Estadual da Bahia (SEFAZ-BA) — esse site NÃO tem captcha, então o sistema
preenche o documento sozinho. Aplica-se só quando a UF for BA."""
from ..base import BaseProvider, registrar
from ...models import TipoPessoa


@registrar
class SefazBA(BaseProvider):
    nome = "CND Estadual (Fazenda) — BA"
    nome_arquivo = "CND_Estadual_BA"
    ufs = ["BA"]
    URL = "https://servicos.sefaz.ba.gov.br/sistemas/DSCRE/Modulos/Publico/EmissaoCertidao.aspx"

    async def abrir(self, ctx, page):
        await page.goto(self.URL, wait_until="domcontentloaded", timeout=60000)
        seletor = "#PHConteudo_TxtNumCNPJ" if ctx.tipo == TipoPessoa.PJ else "#PHConteudo_TxtNumCPF"
        try:
            await page.locator(seletor).fill(ctx.documento, timeout=8000)
        except Exception:
            pass
