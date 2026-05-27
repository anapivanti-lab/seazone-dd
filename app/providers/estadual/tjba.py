"""Certidão da Justiça Estadual da Bahia (TJBA) — 1º grau, modelo Cível.

Fluxo: tipo pessoa → modelo (Cível) → participação Ambas → CPF/CNPJ.
OBS: a página tem um reCAPTCHA (possivelmente invisível); se ele bloquear o
navegador automático, você conclui na tela (o preenchimento já estará feito).
"""
from ..base import BaseProvider, registrar
from ...models import TipoPessoa

URL = "https://portalcertidoes.tjba.jus.br/#/primeirograu"


async def _tentar(*acoes) -> bool:
    for fn in acoes:
        try:
            await fn()
            return True
        except Exception:
            pass
    return False


@registrar
class TJBACivel1(BaseProvider):
    nome = "Justiça Estadual BA — Cível 1º grau"
    nome_arquivo = "TJBA_Civel_1grau"
    ufs = ["BA"]

    async def abrir(self, ctx, page):
        await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)
        pj = ctx.tipo == TipoPessoa.PJ

        await _tentar(
            lambda: page.click("#radioJuridica" if pj else "#radioFisica", timeout=4000),
            lambda: page.click("text=Jurídica" if pj else "text=Física", timeout=3000),
        )
        await page.wait_for_timeout(600)
        await _tentar(
            lambda: page.click("#selectModelo", timeout=4000),
            lambda: page.click("mat-select", timeout=3000),
        )
        await page.wait_for_timeout(700)
        await _tentar(
            lambda: page.click("mat-option:has-text('Cível')", timeout=3000),
            lambda: page.click("text=Certidão Cível", timeout=3000),
        )
        await page.wait_for_timeout(500)
        await _tentar(
            lambda: page.click("#radioAmbas", timeout=3000),
            lambda: page.click("text=Ambas", timeout=3000),
        )
        await page.wait_for_timeout(400)
        await _tentar(
            lambda: page.fill("#mat-input-0", ctx.documento, timeout=4000),
            lambda: page.fill("input[type='text']", ctx.documento, timeout=3000),
        )
