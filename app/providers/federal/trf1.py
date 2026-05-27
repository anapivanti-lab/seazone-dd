"""Certidão da Justiça Federal — TRF1 (BA, DF, GO, MG, MT, MA, PI, PA, AM, AC,
AP, RO, RR, TO). Só funciona no navegador VISÍVEL (bloqueia robô invisível).

Seleciona o Tipo (Cível ou Criminal), o Órgão (Seção Judiciária da UF), marca
CPF/CNPJ e preenche o documento. Você resolve o reCAPTCHA e clica em "Emitir".

Calibrado em 27/05/2026: #mat-select-0 = Tipo; mat-radio-2 = CPF, mat-radio-3 =
CNPJ; campo do documento = input[formcontrolname='cnpj'|'cpf'].
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


class _TRF1Base(BaseProvider):
    """Base do TRF1 — muda só o tipo de certidão (Cível/Criminal)."""
    ufs = list(ORGAO_KW.keys())
    tipo_certidao = "Cível"  # "Cível" | "Criminal"

    async def abrir(self, ctx, page):
        await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        # espera o formulário Angular montar de fato (não um tempo fixo "no escuro")
        try:
            await page.wait_for_selector("#mat-select-0", state="visible", timeout=20000)
        except Exception:
            await page.wait_for_timeout(6000)
        await page.wait_for_timeout(1200)

        # 1) Tipo de Certidão (Cível / Criminal) — abre, clica e CONFIRMA; repete se falhar
        for _ in range(3):
            await _t(lambda: page.click("#mat-select-0", timeout=4000),
                     lambda: page.click("[formcontrolname='tipoCertidaoControl']", timeout=3000))
            await page.wait_for_timeout(900)
            await _t(lambda: page.click(f"mat-option:has-text('{self.tipo_certidao}')", timeout=4000))
            await page.wait_for_timeout(800)
            try:
                txt = await page.eval_on_selector("#mat-select-0", "e => e.innerText")
                if self.tipo_certidao.lower() in (txt or "").lower():
                    break
            except Exception:
                break

        # 2) Órgão = Seção Judiciária da UF
        kw = ORGAO_KW.get(ctx.uf, ctx.uf)
        await _t(lambda: page.fill("#mat-chip-list-input-0", kw, timeout=4000))
        await page.wait_for_timeout(1600)
        await _t(lambda: page.click(f"mat-option:has-text('{kw}')", timeout=4000))
        await page.wait_for_timeout(700)

        # 3) CPF/CNPJ — mat-radio-2 = CPF, mat-radio-3 = CNPJ (ids fixos, confirmados)
        if ctx.tipo == TipoPessoa.PJ:
            await _t(lambda: page.click("#mat-radio-3", timeout=4000),
                     lambda: page.click("#mat-radio-3 label", timeout=3000),
                     lambda: page.check("#mat-radio-3-input", timeout=3000))
            await page.wait_for_timeout(800)
            await _t(lambda: page.fill("input[formcontrolname='cnpj']", ctx.documento, timeout=4000),
                     lambda: page.fill("#mat-input-1", ctx.documento, timeout=3000))
        else:
            await _t(lambda: page.click("#mat-radio-2", timeout=4000),
                     lambda: page.click("#mat-radio-2 label", timeout=3000),
                     lambda: page.check("#mat-radio-2-input", timeout=3000))
            await page.wait_for_timeout(600)
            await _t(lambda: page.fill("input[formcontrolname='cpf']", ctx.documento, timeout=4000),
                     lambda: page.fill("#mat-input-1", ctx.documento, timeout=3000))


@registrar
class TRF1Civel(_TRF1Base):
    nome = "Justiça Federal TRF1 — Cível"
    nome_arquivo = "TRF1_Civel"
    tipo_certidao = "Cível"


@registrar
class TRF1Criminal(_TRF1Base):
    nome = "Justiça Federal TRF1 — Criminal"
    nome_arquivo = "TRF1_Criminal"
    tipo_certidao = "Criminal"
