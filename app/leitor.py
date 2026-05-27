"""Leitor de processos judiciais: extrai o texto do PDF e levanta os dados-chave
(número, partes, valores, tipo/risco). 100% local e gratuito (sem IA paga).

Você baixa o PDF do processo (Jusbrasil/tribunal) e sobe aqui; o sistema lê e
resume os pontos importantes para a análise de risco.
"""
from __future__ import annotations

import re

from pypdf import PdfReader

_RISCOS = {
    "Criminal": ["criminal", "penal", " crime", "estelionato", "furto", "roubo",
                 "apropriação indébita", "lavagem de dinheiro", "ação penal"],
    "Fraude": ["fraude", "fraudulent", "falsidade", "falsific", "simulação", "procuração falsa"],
    "Execução": ["execução", "exequente", "executado", "penhora", "execução fiscal"],
    "Trabalhista": ["reclamante", "reclamada", "trabalhista", "verbas rescisórias", "vínculo empregatício"],
    "Cível/Cobrança": ["indenização", "danos morais", "cobrança", "monitória", "rescisão contratual"],
}

_ROTULOS_PARTE = ["Autor", "Autora", "Réu", "Requerente", "Requerido", "Exequente",
                  "Executado", "Reclamante", "Reclamada", "Embargante", "Embargado"]


def _extrair_texto(caminho: str) -> str:
    try:
        r = PdfReader(caminho)
        return "\n".join((p.extract_text() or "") for p in r.pages)
    except Exception:
        return ""


def analisar(caminho: str) -> dict:
    texto = _extrair_texto(caminho)
    plano = " ".join(texto.split())
    low = plano.lower()

    nproc = re.search(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}", plano)
    valores = re.findall(r"R\$\s?[\d\.]{1,15},\d{2}", plano)

    partes = {}
    for rot in _ROTULOS_PARTE:
        m = re.search(rot + r"[:\s]+([A-ZÀ-Ú][\wÀ-ú .&-]{3,60})", texto)
        if m:
            partes[rot] = m.group(1).strip()

    riscos = [cat for cat, kws in _RISCOS.items() if any(k in low for k in kws)]

    return {
        "numero": nproc.group(0) if nproc else "(não identificado)",
        "partes": partes,
        "valores": list(dict.fromkeys(valores))[:6],
        "riscos": riscos,
        "criminal": "Criminal" in riscos,
        "fraude": "Fraude" in riscos,
        "tem_texto": bool(plano),
    }
