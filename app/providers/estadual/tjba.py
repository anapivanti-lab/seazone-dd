"""Certidões da Justiça Estadual da Bahia (TJBA) — 1º e 2º grau, Cível e Criminal.

Calibrado em 27/05/2026. Usa o quadro "GERAR Certidão" (NÃO o "Consultar", que
pede nº de certidão já emitida). Fluxo idêntico nos dois graus:
  1) Tipo Pessoa (radioFisica/radioJuridica)
  2) Modelo (#selectModelo, via select_option — o Angular só "vê" assim)
  3) Tipo Participação = Ambas (radioAmbas)
  -> aí surgem os botões "Avançar" (<input type=submit>); clica o 1º (Gerar)
  4) 2ª tela:
       PJ: #razaoSocial, #cnpj, #endereco
       PF: #nome, #cpf, #rg, #endereco, #filiacao1 (Nome da Mãe)
NÃO se preenche CPF/CNPJ na 1ª tela (esse campo é do quadro "Consultar").
Página tem reCAPTCHA (invisível); você valida e emite.
"""
import re
import unicodedata

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


def _fmt_doc(doc: str, pj: bool) -> str:
    """Formata CPF/CNPJ (alguns campos do TJBA têm máscara e recusam só dígitos)."""
    d = re.sub(r"\D", "", doc or "")
    if pj and len(d) == 14:
        return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"
    if not pj and len(d) == 11:
        return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
    return d


def _raiz(s: str) -> str:
    """Raiz do estado civil para casar com a opção do site (ex.: 'Solteiro(a)'->'SOLTE')."""
    s = "".join(c for c in unicodedata.normalize("NFKD", s or "") if not unicodedata.combining(c))
    return re.sub(r"[^A-Za-z]", "", s).upper()[:5]


async def _escolher_estado_civil(page, valor: str) -> None:
    raiz = _raiz(valor)
    if not raiz:
        return
    try:
        await page.evaluate(
            """(raiz) => {
            const s = document.querySelector('#selectEstadoCivil'); if (!s) return;
            const norm = t => t.normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toUpperCase();
            const o = [...s.options].find(o => norm(o.text).includes(raiz));
            if (o) { s.value = o.value; s.dispatchEvent(new Event('change', {bubbles: true})); }
        }""",
            raiz,
        )
    except Exception:
        pass


async def _escolher_modelo(page, palavra: str) -> bool:
    """Seleciona no #selectModelo a opção que contém a palavra (cível/criminal),
    via select_option — assim dispara os eventos que o formulário Angular exige
    para liberar o botão 'Avançar'."""
    try:
        val = await page.evaluate(
            """(p) => { const s = document.querySelector('#selectModelo'); if (!s) return null;
            const o = [...s.options].find(o => o.text.toLowerCase().includes(p)); return o ? o.value : null; }""",
            palavra,
        )
        if val is None:
            return False
        await page.select_option("#selectModelo", value=val)
        return True
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


async def _avancar(page) -> bool:
    """Clica o 1º 'Avançar' (do quadro Gerar). É um <input type=submit>, então
    o seletor de <button> não basta — get_by_role pega o value como nome."""
    for fn in (
        lambda: page.get_by_role("button", name="Avançar").first.click(timeout=4000),
        lambda: page.locator("input[type=submit][value*='Avan']").first.click(timeout=3000),
        lambda: page.locator("button:has-text('Avançar')").first.click(timeout=3000),
    ):
        try:
            await fn()
            return True
        except Exception:
            pass
    return False


class _TJBABase(BaseProvider):
    """Emissão no TJBA. Subclasses definem url e o modelo (cível/criminal)."""
    ufs = ["BA"]
    url = URL_1
    modelo_kw = "cível"

    async def abrir(self, ctx, page):
        await page.goto(self.url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4500)
        await _marcar_pessoa(page, ctx)
        await page.wait_for_timeout(700)
        await _escolher_modelo(page, self.modelo_kw)
        await page.wait_for_timeout(800)
        await _tentar(
            lambda: page.click("label:has-text('Ambas')", timeout=3000),
            lambda: page.check("#radioAmbas", timeout=3000),
            lambda: page.click("#radioAmbas", timeout=3000),
        )
        await page.wait_for_timeout(900)
        await _avancar(page)
        await page.wait_for_timeout(2500)
        # espera a 2ª tela montar (campo-chave de PJ ou PF)
        alvo = "#razaoSocial" if ctx.tipo == TipoPessoa.PJ else "#cpf"
        try:
            await page.wait_for_selector(alvo, timeout=6000)
        except Exception:
            await page.wait_for_timeout(1500)
        # 2ª tela — preenche conforme PJ ou PF (você valida o captcha e emite)
        if ctx.tipo == TipoPessoa.PJ:
            await _tentar(lambda: page.fill("#razaoSocial", ctx.nome, timeout=4000))
            await _tentar(lambda: page.fill("#cnpj", _fmt_doc(ctx.documento, True), timeout=4000))
            await _tentar(lambda: page.fill("#endereco", ctx.endereco, timeout=4000))
        else:
            await _tentar(lambda: page.fill("#nome", ctx.nome, timeout=4000))
            await _tentar(lambda: page.fill("#nacionalidade", ctx.nacionalidade or "Brasileira", timeout=3000))
            await _escolher_estado_civil(page, ctx.estado_civil)
            await _tentar(lambda: page.fill("#cpf", _fmt_doc(ctx.documento, False), timeout=4000))
            await _tentar(lambda: page.fill("#rg", ctx.rg, timeout=3000))
            await _tentar(lambda: page.fill("#orgao", ctx.orgao_expedidor, timeout=3000))
            await _tentar(lambda: page.fill("#endereco", ctx.endereco, timeout=3000))
            await _tentar(lambda: page.fill("#filiacao1", ctx.nome_mae, timeout=3000))
            await _tentar(lambda: page.fill("#filiacao2", ctx.nome_pai, timeout=3000))


@registrar
class TJBACivel1(_TJBABase):
    nome = "Justiça Estadual BA — Cível 1º grau"
    nome_arquivo = "TJBA_Civel_1grau"
    url = URL_1
    modelo_kw = "cível"


@registrar
class TJBACriminal1(_TJBABase):
    nome = "Justiça Estadual BA — Criminal 1º grau"
    nome_arquivo = "TJBA_Criminal_1grau"
    url = URL_1
    modelo_kw = "criminal"


@registrar
class TJBACivel2(_TJBABase):
    nome = "Justiça Estadual BA — Cível 2º grau"
    nome_arquivo = "TJBA_Civel_2grau"
    url = URL_2
    modelo_kw = "cível"


@registrar
class TJBACriminal2(_TJBABase):
    nome = "Justiça Estadual BA — Criminal 2º grau"
    nome_arquivo = "TJBA_Criminal_2grau"
    url = URL_2
    modelo_kw = "criminal"
