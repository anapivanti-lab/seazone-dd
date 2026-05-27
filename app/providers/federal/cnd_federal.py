"""CND Federal — Certidão de Débitos relativos a Tributos Federais e à Dívida
Ativa da União (Receita Federal + PGFN). Serve para PJ (CNPJ) e PF (CPF).

Os seletores são um ponto de partida; calibramos na primeira execução real.
"""
from ..base import BaseProvider, registrar
from ...models import Contexto, TipoPessoa

URL_PJ = "https://solucoes.receita.fazenda.gov.br/Servicos/certidaointernet/PJ/Emitir"
URL_PF = "https://solucoes.receita.fazenda.gov.br/Servicos/certidaointernet/PF/Emitir"


@registrar
class CNDFederal(BaseProvider):
    nome = "CND Federal (Receita/PGFN)"
    nivel = "federal"

    async def emitir(self, ctx: Contexto, page):
        url = URL_PJ if ctx.tipo == TipoPessoa.PJ else URL_PF

        async def preencher(page, ctx):
            campo = page.locator("input[name*='NI'], #NI, input[type='text']").first
            await campo.fill(ctx.documento)

        return await self._fluxo_assistido(page, ctx, url, "CND_Federal", preencher)
