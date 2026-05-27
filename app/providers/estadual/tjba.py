"""Certidões da Justiça Estadual da Bahia (TJBA) — 1º e 2º grau, Cível e Criminal.

Calibrado em 27/05/2026. O fluxo de EMISSÃO ("Gerar Certidão") é igual nos dois
graus:
  Tipo Pessoa (radioFisica/radioJuridica) → Modelo (#selectModelo) →
  Tipo Participação (radioAmbas) → CPF/CNPJ → Avançar →
  (PJ) Razão Social/CNPJ/Endereço (#razaoSocial/#cnpj/#endereco).
Diferenças: a URL e o campo do documento (1º grau = #mat-input-0; 2º grau =
#documento). O quadro "Consultar Certidão" (que pede nº da certidão) NÃO é usado.
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
    """No #selectModelo, escolhe a opção que contém a palavra-chave (cível/criminal)
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


class _TJBABase(BaseProvider):
    """Emissão no TJBA. Subclasses definem url, campo do doc e o modelo."""
    ufs = ["BA"]
    url = URL_1
    doc_sel = "#mat-input-0"
    modelo_kw = "cível"

    async def abrir(self, ctx, page):
        await page.goto(self.url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)
        await _marcar_pessoa(page, ctx)
        await page.wait_for_timeout(700)
        await _escolher_modelo(page, self.modelo_kw)
        await page.wait_for_timeout(700)
        # Tipo de participação: Ambas
        await _tentar(
            lambda: page.click("label:has-text('Ambas')", timeout=3000),
            lambda: page.check("#radioAmbas", timeout=3000),
            lambda: page.click("#radioAmbas", timeout=3000),
        )
        await page.wait_for_timeout(500)
        # CPF/CNPJ (1º grau = #mat-input-0; 2º grau = #documento)
        await _tentar(
            lambda: page.fill(self.doc_sel, ctx.documento, timeout=4000),
            lambda: page.fill("#mat-input-0", ctx.documento, timeout=2500),
            lambda: page.fill("#documento", ctx.documento, timeout=2500),
        )
        await page.wait_for_timeout(500)
        # Avançar (o 1º botão "Avançar" é o do quadro "Gerar")
        await _tentar(lambda: page.click("button:has-text('Avançar')", timeout=4000))
        await page.wait_for_timeout(3500)
        # 2ª tela (PJ): Razão Social, CNPJ, Endereço
        if ctx.tipo == TipoPessoa.PJ:
            await _tentar(lambda: page.fill("#razaoSocial", ctx.nome, timeout=4000))
            await _tentar(lambda: page.fill("#cnpj", ctx.documento, timeout=4000))
            await _tentar(lambda: page.fill("#endereco", ctx.endereco, timeout=4000))


@registrar
class TJBACivel1(_TJBABase):
    nome = "Justiça Estadual BA — Cível 1º grau"
    nome_arquivo = "TJBA_Civel_1grau"
    url = URL_1
    doc_sel = "#mat-input-0"
    modelo_kw = "cível"


@registrar
class TJBACriminal1(_TJBABase):
    nome = "Justiça Estadual BA — Criminal 1º grau"
    nome_arquivo = "TJBA_Criminal_1grau"
    url = URL_1
    doc_sel = "#mat-input-0"
    modelo_kw = "criminal"


@registrar
class TJBACivel2(_TJBABase):
    nome = "Justiça Estadual BA — Cível 2º grau"
    nome_arquivo = "TJBA_Civel_2grau"
    url = URL_2
    doc_sel = "#documento"
    modelo_kw = "cível"


@registrar
class TJBACriminal2(_TJBABase):
    nome = "Justiça Estadual BA — Criminal 2º grau"
    nome_arquivo = "TJBA_Criminal_2grau"
    url = URL_2
    doc_sel = "#documento"
    modelo_kw = "criminal"
