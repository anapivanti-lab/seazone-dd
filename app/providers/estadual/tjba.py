"""Certidões da Justiça Estadual da Bahia (TJBA) — 1º e 2º grau, Cível e Criminal.

Calibrado em 27/05/2026:
- 1º grau (#/primeirograu): Tipo Pessoa (radioFisica/radioJuridica) → Modelo
  (#selectModelo: "Certidão Cível" / "Certidão Criminal e Exec. Penal") →
  Tipo Participação (radioAmbas) → CPF/CNPJ (#mat-input-0) → Avançar →
  (PJ) Razão Social/CNPJ/Endereço (#razaoSocial/#cnpj/#endereco).
- 2º grau (#/segundograu): Tipo Pessoa → Modelo ("2º grau cível"/"2º grau
  criminal") → CPF/CNPJ (#documento) + Número da Certidão (#certidao, do 1º grau
  — VOCÊ cola à mão) → Consultar.
Página tem reCAPTCHA (invisível); você valida e emite.
"""
from ..base import BaseProvider, registrar
from ...models import TipoPessoa

URL_1 = "https://portalcertidoes.tjba.jus.br/#/primeirograu"
URL_2 = "https://portalcertidoes.tjba.jus.br/#/segundograu"


async def _tentar(*acoes) -> bool:
    for fn in acoes:
        try:
            await fn()
            return True
        except Exception:
            pass
    return False


async def _escolher_modelo(page, palavra: str) -> bool:
    """Escolhe no #selectModelo a opção que contém a palavra-chave (cível/criminal)
    e dispara o 'change' (o Angular escuta)."""
    try:
        return await page.evaluate(
            """(palavra) => {
            const sel = document.querySelector('#selectModelo');
            if (!sel) return false;
            const alvo = [...sel.options].find(o => o.text.toLowerCase().includes(palavra));
            if (!alvo) return false;
            sel.value = alvo.value;
            sel.dispatchEvent(new Event('change', {bubbles: true}));
            return true;
        }""",
            palavra,
        )
    except Exception:
        return False


async def _marcar_pessoa(page, ctx):
    pessoa = "Jurídica" if ctx.tipo == TipoPessoa.PJ else "Física"
    rid = "#radioJuridica" if ctx.tipo == TipoPessoa.PJ else "#radioFisica"
    await _tentar(
        lambda: page.click(f"label:has-text('{pessoa}')", timeout=4000),
        lambda: page.check(rid, timeout=3000),
        lambda: page.click(rid, timeout=3000),
    )


class _TJBA1Base(BaseProvider):
    """1º grau — muda só o Modelo (Cível/Criminal)."""
    ufs = ["BA"]
    modelo_kw = "cível"

    async def abrir(self, ctx, page):
        await page.goto(URL_1, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)
        await _marcar_pessoa(page, ctx)
        await page.wait_for_timeout(700)
        await _escolher_modelo(page, self.modelo_kw)
        await page.wait_for_timeout(600)
        await _tentar(
            lambda: page.click("label:has-text('Ambas')", timeout=3000),
            lambda: page.check("#radioAmbas", timeout=3000),
        )
        await page.wait_for_timeout(500)
        await _tentar(lambda: page.fill("#mat-input-0", ctx.documento, timeout=4000))
        await page.wait_for_timeout(400)
        await _tentar(
            lambda: page.click("button:has-text('Avançar')", timeout=4000),
            lambda: page.click("button:has-text('Consultar')", timeout=3000),
        )
        await page.wait_for_timeout(3500)
        if ctx.tipo == TipoPessoa.PJ:
            await _tentar(lambda: page.fill("#razaoSocial", ctx.nome, timeout=4000))
            await _tentar(lambda: page.fill("#cnpj", ctx.documento, timeout=4000))
            await _tentar(lambda: page.fill("#endereco", ctx.endereco, timeout=4000))


class _TJBA2Base(BaseProvider):
    """2º grau — preenche tudo, menos o Número da Certidão do 1º grau (você cola)."""
    ufs = ["BA"]
    modelo_kw = "cível"

    async def abrir(self, ctx, page):
        await page.goto(URL_2, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)
        await _marcar_pessoa(page, ctx)
        await page.wait_for_timeout(700)
        await _escolher_modelo(page, self.modelo_kw)
        await page.wait_for_timeout(600)
        await _tentar(
            lambda: page.fill("#documento", ctx.documento, timeout=4000),
            lambda: page.fill("#mat-input-0", ctx.documento, timeout=3000),
        )
        # #certidao (Número da Certidão do 1º grau) você preenche à mão.


@registrar
class TJBACivel1(_TJBA1Base):
    nome = "Justiça Estadual BA — Cível 1º grau"
    nome_arquivo = "TJBA_Civel_1grau"
    modelo_kw = "cível"


@registrar
class TJBACriminal1(_TJBA1Base):
    nome = "Justiça Estadual BA — Criminal 1º grau"
    nome_arquivo = "TJBA_Criminal_1grau"
    modelo_kw = "criminal"


@registrar
class TJBACivel2(_TJBA2Base):
    nome = "Justiça Estadual BA — Cível 2º grau"
    nome_arquivo = "TJBA_Civel_2grau"
    modelo_kw = "cível"


@registrar
class TJBACriminal2(_TJBA2Base):
    nome = "Justiça Estadual BA — Criminal 2º grau"
    nome_arquivo = "TJBA_Criminal_2grau"
    modelo_kw = "criminal"
