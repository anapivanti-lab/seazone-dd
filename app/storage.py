"""Cria a pasta da franquia e gera o relatório de status."""
from __future__ import annotations

import json
import re
from pathlib import Path

from .config import PASTA_SAIDA
from .models import Contexto


def _slug(texto: str) -> str:
    """Transforma 'Fulano Imóveis Ltda' em 'Fulano_Imoveis_Ltda' (nome de pasta)."""
    texto = (texto or "").strip()
    texto = re.sub(r"[^\w\s-]", "", texto, flags=re.UNICODE)
    texto = re.sub(r"\s+", "_", texto)
    return texto[:60] or "sem_nome"


def preparar_pasta(ctx: Contexto) -> Path:
    """Cria (se preciso) e devolve a pasta da franquia/pessoa."""
    rotulo = _slug(ctx.nome) if ctx.nome else ctx.documento
    pasta = PASTA_SAIDA / f"{rotulo}_{ctx.documento}"
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def salvar_relatorio(job) -> Path:
    """Salva relatorio.json (dados) e relatorio.html (legível) na pasta."""
    dados = job.to_dict()
    (job.ctx.pasta_saida / "relatorio.json").write_text(
        json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    destino_html = job.ctx.pasta_saida / "relatorio.html"
    destino_html.write_text(_html_relatorio(dados), encoding="utf-8")
    return destino_html


_ROTULOS = {
    "sucesso": ("✅", "Emitida"),
    "pendente_captcha": ("⏳", "Pendente / calibrar"),
    "indisponivel": ("⚠️", "Indisponível"),
    "erro": ("❌", "Erro"),
}


def _html_relatorio(d: dict) -> str:
    linhas = ""
    for p in d["passos"]:
        icone, texto = _ROTULOS.get(p["status"], ("•", p["status"]))
        arq = (
            f'<a href="{Path(p["arquivo"]).name}">abrir</a>' if p.get("arquivo") else "—"
        )
        linhas += (
            f"<tr><td>{icone} {texto}</td><td>{p['nome']}</td>"
            f"<td>{p.get('mensagem', '')}</td><td>{arq}</td></tr>"
        )
    return f"""<!doctype html><html lang="pt-br"><head><meta charset="utf-8">
<title>Relatório DD — {d['nome'] or d['documento']}</title>
<style>body{{font-family:Segoe UI,Arial,sans-serif;margin:2rem;color:#1a1a1a}}
table{{border-collapse:collapse;width:100%;margin-top:1rem}}
td,th{{border:1px solid #ddd;padding:.5rem;text-align:left}}th{{background:#f5f5f5}}</style>
</head><body>
<h1>Relatório de Due Diligence</h1>
<p><b>{d['tipo']}</b> — {d['nome'] or '(sem nome)'} — {d['documento']}<br>
{d['municipio']}/{d['uf']}</p>
<table><tr><th>Status</th><th>Certidão</th><th>Observação</th><th>Arquivo</th></tr>
{linhas}</table></body></html>"""
