"""Certidão de Protestos — CENPROT (consulta nacional de protestos). PJ e PF."""
from ..base import BaseProvider, registrar

URL = "https://site.cenprot.org.br/consulta-protesto"


@registrar
class Protestos(BaseProvider):
    nome = "Certidão de Protestos (CENPROT)"
    nivel = "nacional"

    async def emitir(self, ctx, page):
        async def preencher(page, ctx):
            campo = page.locator("input[name*='documento'], input[type='text']").first
            await campo.fill(ctx.documento)

        return await self._fluxo_assistido(page, ctx, URL, "Protestos_CENPROT", preencher)
