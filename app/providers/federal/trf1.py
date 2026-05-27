"""Certidão da Justiça Federal — TRF1 (BA, DF, GO, MG, MT, MA, PI, PA, AM, AC,
AP, RO, RR, TO). Só funciona no navegador VISÍVEL (bloqueia robô invisível).

Seleciona Tipo "Cível", o Órgão (Seção Judiciária da UF), marca CPF/CNPJ e
preenche o documento. Você resolve o reCAPTCHA e clica em "Emitir Certidão".
"""
from ..base import BaseProvider, registrar
from ...models import TipoPessoa

URL = "https://sistemas.trf1.jus.br/certidao/#/solicitacao"

ORGAO_KW = {
    "BA": "BAHIA", "DF": "DISTRITO FEDERAL", "GO": "GOIÁS", "MG": "MINAS GERAIS",
    "MT": "MATO GROSSO", "MA": "MARANHÃO", "PI": "PIAUÍ", "PA": "PARÁ",
    "AM": "AMAZONAS", "AC": "ACRE", "AP": "AMAPÁ", "RO": "RONDÔNIA",
    "RR": "RORAIMA", "TO": "TOCANTINS",
}


async def _t(*acoes) -> bool:
    for fn in acoes:
        try:
            await fn()
            return True
        except Exception:
            pass
    return False


@registrar
class TRF1Civel(BaseProvider):
    nome = "Justiça Federal TRF1 — Cível"
    nome_arquivo = "TRF1_Civel"
    ufs = list(ORGAO_KW.keys())

    async def abrir(self, ctx, page):
        await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(6000)
        # Tipo de Certidão = Cível
        await _t(lambda: page.click("#mat-select-0", timeout=5000),
                 lambda: page.click("[formcontrolname='tipoCertidaoControl']", timeout=4000))
        await page.wait_for_timeout(1000)
        await _t(lambda: page.click("mat-option:has-text('Cível')", timeout=4000))
        await page.wait_for_timeout(800)
        # Órgão = Seção Judiciária da UF
        kw = ORGAO_KW.get(ctx.uf, ctx.uf)
        await _t(lambda: page.fill("#mat-chip-list-input-0", kw, timeout=4000))
        await page.wait_for_timeout(1500)
        await _t(lambda: page.click(f"mat-option:has-text('{kw}')", timeout=4000))
        await page.wait_for_timeout(600)
        # CPF/CNPJ
        if ctx.tipo == TipoPessoa.PJ:
            await _t(lambda: page.click("label:has-text('CNPJ')", timeout=3000),
                     lambda: page.click("mat-radio-button:has-text('CNPJ')", timeout=3000),
                     lambda: page.click("text=CNPJ", timeout=2500))
            await page.wait_for_timeout(500)
        # Documento
        await _t(lambda: page.fill("input[formcontrolname='cnpj']", ctx.documento, timeout=3000),
                 lambda: page.fill("input[formcontrolname='cpf']", ctx.documento, timeout=3000),
                 lambda: page.fill("#mat-input-0", ctx.documento, timeout=3000))
