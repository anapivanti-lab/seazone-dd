"""CNDT — Certidão Negativa de Débitos Trabalhistas (TST). PJ e PF.

Fluxo: abre a página, clica em "Emitir Certidão", preenche o CNPJ/CPF.
Sobra para você só digitar o captcha (imagem) e emitir — o PDF é capturado.
"""
from ..base import BaseProvider, registrar

URL = "https://cndt-certidao.tst.jus.br/inicio.faces"


@registrar
class CNDTrabalhista(BaseProvider):
    nome = "CND Trabalhista (TST)"
    nome_arquivo = "CND_Trabalhista"

    async def abrir(self, ctx, page):
        await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        try:
            await page.click("input[value*='Emitir']", timeout=8000)
            await page.wait_for_timeout(1800)
        except Exception:
            pass
        try:
            await page.fill("[id='gerarCertidaoForm:cpfCnpj']", ctx.documento, timeout=8000)
        except Exception:
            pass
