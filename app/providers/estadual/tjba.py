"""Certidão da Justiça Estadual da Bahia (TJBA) — 1º grau, modelo Cível.

Fluxo (calibrado): tipo pessoa → Modelo Cível → participação Ambas → CPF/CNPJ
→ Avançar. A página tem reCAPTCHA (invisível); se barrar, você conclui na tela.
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
        pessoa = "Jurídica" if ctx.tipo == TipoPessoa.PJ else "Física"

        await _tentar(
            lambda: page.click(f"label:has-text('{pessoa}')", timeout=5000),
            lambda: page.click(f"text={pessoa}", timeout=3000),
        )
        await page.wait_for_timeout(700)

        # Modelo "Certidão Cível" — tenta select nativo; se não, abre e clica a opção
        modelo_ok = await _tentar(
            lambda: page.select_option("#selectModelo", label="Certidão Cível"),
        )
        if not modelo_ok:
            await _tentar(lambda: page.click("#selectModelo", timeout=3000),
                          lambda: page.click("mat-select", timeout=3000))
            await page.wait_for_timeout(800)
            await _tentar(
                lambda: page.click("mat-option:has-text('Cível')", timeout=3000),
                lambda: page.click(".mat-option:has-text('Cível')", timeout=3000),
                lambda: page.click("text=Certidão Cível", timeout=3000),
            )
        await page.wait_for_timeout(600)

        await _tentar(
            lambda: page.click("label:has-text('Ambas')", timeout=3000),
            lambda: page.click("text=Ambas", timeout=3000),
        )
        await page.wait_for_timeout(500)

        await _tentar(
            lambda: page.fill("#mat-input-0", ctx.documento, timeout=4000),
            lambda: page.fill("input[placeholder*='CNPJ']", ctx.documento, timeout=3000),
            lambda: page.fill("input[placeholder*='CPF']", ctx.documento, timeout=3000),
        )
        await page.wait_for_timeout(500)

        # Avança para a 2ª tela
        await _tentar(
            lambda: page.click("button:has-text('Avançar')", timeout=4000),
            lambda: page.click("input[value*='Avan']", timeout=3000),
        )
        await page.wait_for_timeout(3500)
        # 2ª tela (PJ): Razão Social, CNPJ e Endereço Completo
        if ctx.tipo == TipoPessoa.PJ:
            await _tentar(lambda: page.fill("#razaoSocial", ctx.nome, timeout=4000))
            await _tentar(lambda: page.fill("#cnpj", ctx.documento, timeout=4000))
            await _tentar(lambda: page.fill("#endereco", ctx.endereco, timeout=4000))
