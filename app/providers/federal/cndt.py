"""CNDT — Certidão Negativa de Débitos Trabalhistas (TST). Serve para PJ e PF."""
from ..base import BaseProvider, registrar

URL = "https://cndt-certidao.tst.jus.br/inicio.faces"


@registrar
class CNDTrabalhista(BaseProvider):
    nome = "CND Trabalhista (TST)"
    nivel = "federal"

    async def emitir(self, ctx, page):
        async def preencher(page, ctx):
            campo = page.locator("input[id*='cpfCnpj'], input[type='text']").first
            await campo.fill(ctx.documento)

        return await self._fluxo_assistido(page, ctx, URL, "CND_Trabalhista", preencher)
