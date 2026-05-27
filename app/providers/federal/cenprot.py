"""Certidão de Protestos — CENPROT (consulta nacional). PJ e PF.

Abre a consulta no navegador automático (com o certificado disponível para
login) e preenche o documento. Você resolve o captcha e consulta.
"""
from ..base import BaseProvider, registrar

URL = "https://www.pesquisaprotesto.com.br/servico/consulta-documento"


@registrar
class Protestos(BaseProvider):
    nome = "Certidão de Protestos (CENPROT)"
    nome_arquivo = "Protestos_CENPROT"
    nivel = "nacional"

    async def abrir(self, ctx, page):
        await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(2500)
        try:
            await page.fill("#cpf_cnpj", ctx.documento, timeout=8000)
        except Exception:
            pass
