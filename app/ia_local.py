"""IA LOCAL (Ollama) — gratuita, roda na própria máquina (sem custo de API, sem
nada saindo do computador). Usada para resumir processos em linguagem simples no
parecer. Se o Ollama não estiver instalado/rodando, o sistema cai no resumo por
regras (fallback) — nada quebra.
"""
from __future__ import annotations

import re

import httpx

try:
    from .config_local import MODELO_IA
except Exception:
    MODELO_IA = "llama3.2:3b"

_BASE = "http://localhost:11434"


def disponivel() -> bool:
    try:
        return httpx.get(f"{_BASE}/api/tags", timeout=3).status_code == 200
    except Exception:
        return False


def _gerar(prompt: str, timeout: int = 180) -> str:
    try:
        r = httpx.post(f"{_BASE}/api/generate", json={
            "model": MODELO_IA, "prompt": prompt, "stream": False,
            "options": {"temperature": 0.1, "num_predict": 350},
        }, timeout=timeout)
        if r.status_code == 200:
            return (r.json().get("response") or "").strip()
    except Exception:
        pass
    return ""


def resumir_processo(pr: dict, sujeito: str) -> str:
    """Resumo do processo em português simples (2 a 4 frases), via IA local.
    Devolve '' se a IA não estiver disponível ou falhar (usa-se o fallback)."""
    fatos = (pr.get("fatos") or "").strip()
    if not fatos or not disponivel():
        return ""
    prompt = (
        "Você é um assistente jurídico do setor de franquias. Escreva um RESUMO CURTO "
        "(2 a 4 frases), em português claro e simples, SEM juridiquês (sem termos em latim, "
        "sem 'animus', 'in casu' etc.), sobre o processo abaixo, para um parecer de due "
        f"diligence. Explique do que se trata e o que aconteceu, deixando claro a participação "
        f"de {sujeito}. Use APENAS as informações do texto; não invente nada. Comece a frase "
        "por 'Foi localizado o processo'. Responda só o resumo, sem títulos.\n\n"
        f"Número: {pr.get('numero', '')}\nClasse: {pr.get('classe', '')}\n"
        f"Assunto: {pr.get('assunto', '')}\nPapel da pessoa: {pr.get('papel_dd', '')}\n"
        f"Texto dos fatos do processo: {fatos[:2500]}\n\nRESUMO:"
    )
    return re.sub(r"\s+", " ", _gerar(prompt)).strip()
