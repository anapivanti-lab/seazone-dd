"""Consulta gratuita dos dados do CNPJ (CNAE, razão social, situação, sócios)
via BrasilAPI — sem captcha, sem login, sem custo.

Serve para preencher o CNAE (critério de risco nº 3), mostrar a situação
cadastral e listar os sócios (úteis para a checagem de PEP)."""
from __future__ import annotations

import re

import httpx


def consultar(cnpj: str) -> dict | None:
    digitos = re.sub(r"\D", "", cnpj or "")
    if len(digitos) != 14:
        return None
    try:
        r = httpx.get(f"https://brasilapi.com.br/api/cnpj/v1/{digitos}", timeout=20)
        if r.status_code != 200:
            return None
        d = r.json()
    except Exception:
        return None
    return {
        "razao_social": d.get("razao_social") or "",
        "nome_fantasia": d.get("nome_fantasia") or "",
        "cnae_codigo": str(d.get("cnae_fiscal") or ""),
        "cnae_descricao": d.get("cnae_fiscal_descricao") or "",
        "situacao": (d.get("descricao_situacao_cadastral") or "").upper(),
        "uf": d.get("uf") or "",
        "municipio": d.get("municipio") or "",
        "endereco": ", ".join(filter(None, [
            f"{d.get('logradouro', '')} {d.get('numero', '')}".strip(),
            d.get("bairro") or "",
            f"{d.get('municipio', '')}/{d.get('uf', '')}".strip("/"),
            (f"CEP {d.get('cep')}" if d.get("cep") else ""),
        ])),
        "socios": [s.get("nome_socio") for s in (d.get("qsa") or []) if s.get("nome_socio")],
    }
