"""Certidão de Protestos — CENPROT (consulta nacional). PJ e PF.

Fluxo (sem captcha quando logado): /login -> "Continuar utilizando certificado
digital" (o certificado da Seazone é apresentado automaticamente) -> consulta
de CPF/CNPJ -> preenche -> Buscar. Você confere e clica em Imprimir.
"""
from ..base import BaseProvider, registrar

URL_LOGIN = "https://www.pesquisaprotesto.com.br/login"
URL_CONSULTA = "https://www.pesquisaprotesto.com.br/servico/consulta-documento"


@registrar
class Protestos(BaseProvider):
    nome = "Certidão de Protestos (CENPROT)"
    nome_arquivo = "Protestos_CENPROT"
    nivel = "nacional"

    async def abrir(self, ctx, page):
        # 1) Login com o certificado digital
        await page.goto(URL_LOGIN, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(2500)
        for sel in ["text=Continuar utilizando certificado digital",
                    "text=certificado digital", "button:has-text('certificado')"]:
            try:
                await page.click(sel, timeout=6000)
                await page.wait_for_timeout(4000)
                break
            except Exception:
                pass
        # 2) Página de consulta de CPF/CNPJ
        await page.goto(URL_CONSULTA, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(2500)
        try:
            await page.fill("#cpf_cnpj", ctx.documento, timeout=8000)
        except Exception:
            pass
        # 3) Buscar (lupa)
        for sel in ["button:has-text('Buscar')", "button[type='submit']",
                    "[aria-label*='uscar']", ".btn-buscar"]:
            try:
                await page.click(sel, timeout=4000)
                break
            except Exception:
                pass
