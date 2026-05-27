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
    "RS": "https://www.sefaz.rs.gov.br/sat/CertidaoSitFiscalSolic.aspx",
    "PR": "https://cdwfazenda.paas.pr.gov.br/cdwportal/certidao/automatica",
    "DF": "https://ww1.receita.fazenda.df.gov.br/cidadao/certidoes/Certidao",
    "AL": "https://contribuinte.sefaz.al.gov.br/certidao/#/emitir-certidao",
    "PE": "https://efisco.sefaz.pe.gov.br/sfi_trb_gcc/PREmitirCertidaoRegularidadeFiscalMovel",
    "MS": "https://servicos.efazenda.ms.gov.br/pndfis/home/emissao",
    "GO": "https://www.sefaz.go.gov.br/Certidao/Emissao/default.asp",
    "RJ": "https://www.consultadividaativa.rj.gov.br/RDGWEBLNX/servlet/StartCISPage?PAGEURL=/cisnatural/NatLogon.html&xciParameters.natsession=Solicitar_Certidao",
}

# --- Justiça Estadual (Tribunal de Justiça), por UF ---
TJ = {
    "SC": "https://certidoes.tjsc.jus.br/pedidoCertidao",
    "BA": "https://portalcertidoes.tjba.jus.br/#/primeirograu",
    "SP": "https://esaj.tjsp.jus.br/sco/abrirCadastro.do",
    "RS": "https://www.tjrs.jus.br/novo/processos-e-servicos/servicos-processuais/emissao-de-antecedentes-e-certidoes/",
    "AL": "https://www2.tjal.jus.br/sco/abrirCadastro.do?servico=810101",
    "PE": "https://certidoesunificadas.app.tjpe.jus.br/",
    "MS": "https://esaj.tjms.jus.br/sco/abrirCadastro.do",
    "GO": "https://projudi.tjgo.jus.br/CertidaoNegativaPositivaPublica?PaginaAtual=1&TipoArea=2&InteressePessoal=S",
    "DF": "https://cnc.tjdft.jus.br/solicitacao-externa",
}

# --- Justiça Federal, por região (a certidão cobre toda a região do TRF) ---
_TRF1 = "https://sistemas.trf1.jus.br/certidao/#/solicitacao"                   # DF, BA, MG, GO, MT...
_TRF2 = "https://certidoes.trf2.jus.br/certidoes/#/principal/solicitar"         # RJ, ES
_TRF3 = "https://web.trf3.jus.br/certidao-regional/CertidaoCivelEleitoralCriminal/SolicitarDadosCertidao"  # SP, MS
_TRF4 = "https://www2.trf4.jus.br/trf4/processos/certidao/index.php"            # RS, SC, PR
_TRF5 = "https://certidoes.trf5.jus.br/certidoes2022/"                          # AL, PE, CE, PB, RN, SE
TRF = {
    "SC": _TRF4, "RS": _TRF4, "PR": _TRF4,
    "RJ": _TRF2, "ES": _TRF2,
    "SP": _TRF3, "MS": _TRF3,
    "AL": _TRF5, "PE": _TRF5, "CE": _TRF5, "PB": _TRF5, "RN": _TRF5, "SE": _TRF5,
    "BA": _TRF1, "DF": _TRF1, "GO": _TRF1, "MG": _TRF1, "MT": _TRF1, "MA": _TRF1,
    "PI": _TRF1, "PA": _TRF1, "AM": _TRF1, "AC": _TRF1, "AP": _TRF1, "RO": _TRF1, "RR": _TRF1, "TO": _TRF1,
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
        Item("CND Federal (Receita/PGFN)", "Federais", modo="abrir", url=_RECEITA_CND),
        Item("CND Trabalhista (TST)", "Federais", modo="auto", provider="CND Trabalhista (TST)"),
        Item("Certidão de Protestos (CENPROT)", "Federais", modo="abrir",
             url="https://www.pesquisaprotesto.com.br/servico/consulta-documento"),
    ]
    if pj:
        itens.append(Item("Cartão CNPJ (Comprovante de Inscrição)", "Federais",
                           modo="auto", provider="Cartão CNPJ (Comprovante de Inscrição)"))

    uf_ok = bool(uf)
    muni_ok = bool(muni)

    # Estadual (Fazenda) — UFs com provedor que preenche sozinho (você só faz o captcha)
    _sefaz_auto = {
        "BA": "CND Estadual (Fazenda) — BA",
        "SC": "CND Estadual (Fazenda) — SC",
        "SP": "CND Estadual (Fazenda) — SP",
        "RS": "CND Estadual (Fazenda) — RS",
        "PE": "CND Estadual (Fazenda) — PE",
        "MS": "CND Estadual (Fazenda) — MS",
    }
    if uf in _sefaz_auto:
        itens.append(Item("CND Estadual (Fazenda)", "Estaduais", modo="auto", provider=_sefaz_auto[uf]))
    else:
        itens.append(_loc("CND Estadual (Fazenda)", "Estaduais", SEFAZ.get(uf), uf_ok, "UF", f"SEFAZ de {onde_uf}"))

    # Justiça Estadual — alguns itens têm provedor que preenche sozinho
    tj = TJ.get(uf)
    _tj_auto = {
        ("BA", "Cível 1º grau"): "Justiça Estadual BA — Cível 1º grau",
        ("GO", "Criminal 1º grau"): "Justiça Estadual GO — Criminal (antecedentes)",
    }
    for g in _GRAUS:
        prov = _tj_auto.get((uf, g))
        if prov:
            itens.append(Item(f"Justiça Estadual — {g}", "Justiça Estadual", modo="auto", provider=prov))
        else:
            itens.append(_loc(f"Justiça Estadual — {g}", "Justiça Estadual", tj, uf_ok, "UF", f"TJ de {onde_uf}"))

    # Justiça Federal (mesma página do TRF da região)
    trf = TRF.get(uf)
    _trf1_ufs = {"BA", "DF", "GO", "MG", "MT", "MA", "PI", "PA", "AM", "AC", "AP", "RO", "RR", "TO"}
    for g in _GRAUS:
        if g == "Cível 1º grau" and uf in _trf1_ufs:
            itens.append(Item(f"Justiça Federal — {g}", "Justiça Federal",
                              modo="auto", provider="Justiça Federal TRF1 — Cível"))
        else:
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
