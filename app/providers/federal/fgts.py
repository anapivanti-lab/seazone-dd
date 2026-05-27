"""CRF/FGTS — Certificado de Regularidade do FGTS (Caixa).
Apenas PJ (empregador)."""
from ..base import BaseProvider, registrar

URL = "https://consulta-crf.caixa.gov.br/consultacrf/pages/consultaEmpregador.jsf"


@registrar
class FGTS(BaseProvider):
    nome = "Regularidade do FGTS (Caixa)"
    nivel = "federal"
    aplica_pf = False

    async def emitir(self, ctx, page):
        async def preencher(page, ctx):
            campo = page.locator("input[id*='mascaraInscricao'], input[type='text']").first
            await campo.fill(ctx.documento)

        return await self._fluxo_assistido(page, ctx, URL, "FGTS_CRF", preencher)
