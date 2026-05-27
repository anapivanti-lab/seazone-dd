"""Cartão CNPJ — Comprovante de Inscrição e Situação Cadastral (Receita Federal).
Apenas PJ. Também é a fonte do CNAE (usado no critério de risco nº 3)."""
from ..base import BaseProvider, registrar

URL = "https://solucoes.receita.fazenda.gov.br/servicos/cnpjreva/cnpjreva_solicitacao.asp"


@registrar
class CartaoCNPJ(BaseProvider):
    nome = "Cartão CNPJ (Comprovante de Inscrição)"
    nivel = "federal"
    aplica_pf = False

    async def emitir(self, ctx, page):
        async def preencher(page, ctx):
            campo = page.locator("input[name*='cnpj'], input[type='text']").first
            await campo.fill(ctx.documento)

        return await self._fluxo_assistido(page, ctx, URL, "Cartao_CNPJ", preencher)
