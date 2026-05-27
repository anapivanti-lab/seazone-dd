"""Checagem de PEP (Pessoa Politicamente Exposta) via API do Portal da
Transparência. Gratuita, mas exige um token (PORTAL_TOKEN em config_local).

Para PJ, verifica os sócios pelo nome; para PF, verifica pelo CPF.
"""
from __future__ import annotations

import re

import httpx

from .config import PORTAL_TOKEN

_URL = "https://api.portaldatransparencia.gov.br/api-de-dados/peps"


def _norm(s: str) -> str:
    return " ".join((s or "").upper().split())


def _buscar(params: dict):
    if not PORTAL_TOKEN:
        return None
    try:
        r = httpx.get(_URL, params=params,
                      headers={"chave-api-dados": PORTAL_TOKEN, "Accept": "application/json"},
                      timeout=25)
        return r.json() if r.status_code == 200 else []
    except Exception:
        return []


def _formatar(p: dict) -> dict:
    return {"nome": _norm(p.get("nome")), "funcao": _norm(p.get("descricao_funcao")),
            "orgao": _norm(p.get("nome_orgao"))}


def por_cpf(cpf: str) -> list:
    digitos = re.sub(r"\D", "", cpf or "")
    if len(digitos) != 11:
        return []
    return [_formatar(p) for p in (_buscar({"cpf": digitos, "pagina": 1}) or [])]


def por_nome(nome: str) -> list:
    alvo = _norm(nome)
    if len(alvo) < 6:
        return []
    res = _buscar({"nome": alvo, "pagina": 1}) or []
    return [_formatar(p) for p in res if _norm(p.get("nome")) == alvo]  # match exato


def checar(nomes: list | None = None, cpf: str | None = None) -> dict:
    """Devolve {'disponivel': bool, 'pep': [...], 'verificados': [...]}."""
    if not PORTAL_TOKEN:
        return {"disponivel": False, "pep": [], "verificados": []}
    pep, verificados = [], []
    if cpf:
        verificados.append(cpf)
        pep += por_cpf(cpf)
    for nome in (nomes or []):
        verificados.append(nome)
        pep += por_nome(nome)
    return {"disponivel": True, "pep": pep, "verificados": verificados}
