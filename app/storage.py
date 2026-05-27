"""Cria a pasta da franquia e gera o relatório de status."""
from __future__ import annotations

import json
import re
from pathlib import Path

from .config import base_saida
from .models import Contexto


def _slug(texto: str) -> str:
    """Transforma 'CND Federal (Receita)' em 'CND_Federal_Receita' (nome de arquivo)."""
    texto = (texto or "").strip()
    texto = re.sub(r"[^\w\s-]", "", texto, flags=re.UNICODE)
    texto = re.sub(r"\s+", "_", texto)
    return texto[:60] or "documento"


_PREF_PAPEL = {"Franquia": "Franquia", "Representante legal": "Rep. legal", "Operador": "Operador",
               "Representante legal e Operador": "Rep. legal e Operador"}


def prefixo_papel(ctx) -> str:
    """Prefixo do nome dos arquivos por papel — evita colisão quando PJ + 2 PFs
    salvam na MESMA pasta da DD (ex.: 'Operador - CND Federal...pdf')."""
    return _PREF_PAPEL.get(getattr(ctx, "papel", "") or "", "")


def com_prefixo(ctx, base: str) -> str:
    pref = prefixo_papel(ctx)
    return f"{pref} - {base}" if pref else base


def preparar_pasta(ctx: Contexto) -> Path:
    """Pasta da DD no padrão do setor: '#<ID Suporte> - DD - <Operador>'.
    PJ + representante legal + operador compartilham a MESMA pasta (mesmo ID)."""
    operador = (ctx.operador or ctx.nome or ctx.documento).strip()
    nome_pasta = f"#{ctx.id_suporte} - DD - {operador}" if ctx.id_suporte else f"DD - {operador}"
    nome_pasta = re.sub(r'[\\/:*?"<>|]+', "", nome_pasta).strip()[:120] or ctx.documento
    pasta = base_saida() / nome_pasta
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def salvar_relatorio(job) -> Path:
    dados = job.to_dict()
    base = com_prefixo(job.ctx, "relatorio")
    (job.ctx.pasta_saida / f"{base}.json").write_text(
        json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    destino = job.ctx.pasta_saida / f"{base}.html"
    destino.write_text(_html(dados), encoding="utf-8")
    return destino


_ROTULOS = {
    "sucesso": ("✅", "Emitida (auto)"),
    "enviado": ("✅", "Enviado (manual)"),
    "manual": ("📤", "Falta enviar"),
    "pendente": ("⏳", "Pendente"),
    "pendente_captcha": ("⏳", "Pendente"),
    "aberta": ("📂", "Aberta"),
    "aguardando": ("•", "Na fila"),
    "indisponivel": ("⚠️", "Indisponível"),
    "erro": ("❌", "Erro"),
}


def _html(d: dict) -> str:
    linhas = ""
    for p in d["passos"]:
        icone, texto = _ROTULOS.get(p["status"], ("•", p["status"]))
        arq = f'<a href="{Path(p["arquivo"]).name}">abrir</a>' if p.get("arquivo") else "—"
        linhas += (
            f"<tr><td>{icone} {texto}</td><td>{p.get('grupo', '')}</td>"
            f"<td>{p['nome']}</td><td>{p.get('mensagem', '')}</td><td>{arq}</td></tr>"
        )
    return f"""<!doctype html><html lang="pt-br"><head><meta charset="utf-8">
<title>Relatório DD — {d['nome'] or d['documento']}</title>
<style>body{{font-family:Segoe UI,Arial,sans-serif;margin:2rem;color:#1a1a1a}}
table{{border-collapse:collapse;width:100%;margin-top:1rem}}
td,th{{border:1px solid #ddd;padding:.5rem;text-align:left;font-size:.9rem}}
th{{background:#f5f5f5}}</style></head><body>
<h1>Relatório de Due Diligence</h1>
<p><b>{d['tipo']}</b> — {d['nome'] or '(sem nome)'} — {d['documento']}<br>
{d['municipio']}/{d['uf']}</p>
<table><tr><th>Status</th><th>Grupo</th><th>Documento</th><th>Observação</th><th>Arquivo</th></tr>
{linhas}</table></body></html>"""
