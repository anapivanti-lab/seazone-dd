"""Checklist completo da Due Diligence + mapa de sites por UF/município.

MODOS de cada item:
  - "auto"   : navegador controlado abre e captura o PDF (precisa de 'provider').
  - "abrir"  : abre a página no NAVEGADOR NORMAL da usuária (sem detecção de
               robô) e copia o documento; ela valida o captcha, baixa e sobe o
               PDF. Precisa só da 'url'.
  - "manual" : site ainda não cadastrado / pago / sem site -> só upload.

Para cadastrar uma cidade/estado novo, basta acrescentar a URL nos mapas abaixo.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from .models import TipoPessoa


@dataclass
class Item:
    nome: str
    grupo: str
    modo: str = "manual"
    provider: str | None = None
    url: str | None = None
    obs: str = ""


def _norm(texto: str) -> str:
    """minúsculas, sem acento, sem espaços extras (para casar nomes de cidade)."""
    t = (texto or "").strip().lower()
    t = "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))
    return " ".join(t.split())


# --- Federais (fixos) ---
_RECEITA_CND = "https://servicos.receitafederal.gov.br/servico/certidoes/"
_RECEITA_CARTAO = "https://servicos.receita.fazenda.gov.br/servicos/cnpjreva/cnpjreva_solicitacao.asp"

# --- CND Estadual (Fazenda), por UF ---
SEFAZ = {
    "SC": "https://sat.sef.sc.gov.br/tax.NET/Sat.CtaCte.Web/SolicitacaoCnd.aspx",
    "BA": "https://servicos.sefaz.ba.gov.br/sistemas/DSCRE/Modulos/Publico/EmissaoCertidao.aspx",
    "SP": "https://www10.fazenda.sp.gov.br/CertidaoNegativaDeb/Pages/EmissaoCertidaoNegativa.aspx",
}

# --- Justiça Estadual (Tribunal de Justiça), por UF ---
TJ = {
    "SC": "https://certidoes.tjsc.jus.br/pedidoCertidao",
    "BA": "https://portalcertidoes.tjba.jus.br/#/primeirograu",
    "SP": "https://esaj.tjsp.jus.br/sco/abrirCadastro.do",
}

# --- Justiça Federal, por região (a certidão cobre toda a região do TRF) ---
_TRF4 = "https://www2.trf4.jus.br/trf4/processos/certidao/index.php"            # RS, SC, PR
_TRF1 = "https://sistemas.trf1.jus.br/certidao/#/solicitacao"                   # DF, BA, MG, GO...
_TRF3 = "https://web.trf3.jus.br/certidao-regional/CertidaoCivelEleitoralCriminal/SolicitarDadosCertidao"  # SP, MS
TRF = {
    "SC": _TRF4, "RS": _TRF4, "PR": _TRF4,
    "BA": _TRF1, "DF": _TRF1, "GO": _TRF1, "MT": _TRF1, "MA": _TRF1, "PI": _TRF1,
    "PA": _TRF1, "AM": _TRF1, "AC": _TRF1, "AP": _TRF1, "RO": _TRF1, "RR": _TRF1, "TO": _TRF1,
    "SP": _TRF3, "MS": _TRF3,
}

# --- CND Municipal, por município normalizado (str ou {"PJ":..,"PF":..}) ---
MUNICIPAL = {
    "florianopolis": "https://e-gov.betha.com.br/cdweb/03114-558/contribuinte/rel_cndcontribuinte.faces",
    "sao paulo": "https://duc.prefeitura.sp.gov.br/certidoes/forms_anonimo/frmConsultaEmissaoCertificado.aspx",
    "salvador": {
        "PJ": "https://www2.sefaz.salvador.ba.gov.br/servico/certidao-regularidade-fiscal-pj",
        "PF": "https://www2.sefaz.salvador.ba.gov.br/servico/certidao-regularidade-fiscal-pf",
    },
}

_GRAUS = ["Cível 1º grau", "Cível 2º grau", "Criminal 1º grau", "Criminal 2º grau"]


def _loc(nome: str, grupo: str, url, preenchido: bool, oque: str, alvo: str) -> Item:
    """Resolve um item que depende da localização (UF/cidade)."""
    if not preenchido:
        return Item(nome, grupo, modo="local", obs=f"Preencha a {oque} acima para liberar.")
    if url:
        return Item(nome, grupo, modo="abrir", url=url)
    return Item(nome, grupo, modo="manual", obs=f"Site ({alvo}) ainda não cadastrado — envie o PDF.")


def itens_para(ctx) -> list[Item]:
    pj = ctx.tipo == TipoPessoa.PJ
    uf = (ctx.uf or "").upper()
    muni = _norm(ctx.municipio)
    onde_uf = uf or "sua UF"
    onde_mun = ctx.municipio or "seu município"

    itens: list[Item] = [
        Item("CND Federal (Receita/PGFN)", "Federais", modo="auto", provider="CND Federal (Receita/PGFN)"),
        Item("CND Trabalhista (TST)", "Federais", modo="auto", provider="CND Trabalhista (TST)"),
        Item("Certidão de Protestos (CENPROT)", "Federais", modo="auto",
             provider="Certidão de Protestos (CENPROT)"),
    ]
    if pj:
        itens.append(Item("Cartão CNPJ (Comprovante de Inscrição)", "Federais",
                           modo="abrir", url=_RECEITA_CARTAO))

    uf_ok = bool(uf)
    muni_ok = bool(muni)

    # Estadual (Fazenda) — UFs com provedor que preenche sozinho (você só faz o captcha)
    _sefaz_auto = {
        "BA": "CND Estadual (Fazenda) — BA",
        "SC": "CND Estadual (Fazenda) — SC",
        "SP": "CND Estadual (Fazenda) — SP",
    }
    if uf in _sefaz_auto:
        itens.append(Item("CND Estadual (Fazenda)", "Estaduais", modo="auto", provider=_sefaz_auto[uf]))
    else:
        itens.append(_loc("CND Estadual (Fazenda)", "Estaduais", SEFAZ.get(uf), uf_ok, "UF", f"SEFAZ de {onde_uf}"))

    # Justiça Estadual (mesma página do TJ cobre os itens)
    tj = TJ.get(uf)
    for g in _GRAUS:
        if uf == "BA" and g == "Cível 1º grau":
            itens.append(Item(f"Justiça Estadual — {g}", "Justiça Estadual",
                              modo="auto", provider="Justiça Estadual BA — Cível 1º grau"))
        else:
            itens.append(_loc(f"Justiça Estadual — {g}", "Justiça Estadual", tj, uf_ok, "UF", f"TJ de {onde_uf}"))

    # Justiça Federal (mesma página do TRF da região)
    trf = TRF.get(uf)
    for g in _GRAUS:
        itens.append(_loc(f"Justiça Federal — {g}", "Justiça Federal", trf, uf_ok, "UF", f"TRF de {onde_uf}"))

    # Municipal
    mun = MUNICIPAL.get(muni)
    if isinstance(mun, dict):
        mun = mun.get(ctx.tipo.value)
    itens.append(_loc("CND Municipal", "Municipais", mun, muni_ok, "cidade", onde_mun))

    # Você fornece
    if pj:
        itens.append(Item("Contrato Social + última alteração", "Você fornece"))
        itens.append(Item("Identidade dos sócios / representante", "Você fornece"))
    else:
        itens.append(Item("RG e CPF do representante", "Você fornece"))

    return itens
