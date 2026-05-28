"""Controle de Due Diligences INTEGRADO ao sistema: a cada parecer gerado, o
sistema registra/atualiza a DD num cadastro (JSON persistente na pasta das
Franquias). A página /controle mostra todas as DDs numa tabela. Há também
exportação para Excel sob demanda (botão), mas o controle vive no próprio sistema.
"""
from __future__ import annotations

import json
import re
from datetime import datetime

from .config import base_saida

ARQ_REG = "_controle_dds.json"
_COR = {"ALTO": ("#c0392b", "#f8d7da"), "MÉDIO": ("#b8860b", "#fff3cd"), "BAIXO": ("#1a7d3c", "#d4edda")}


def _fmt(doc: str, pj: bool) -> str:
    d = re.sub(r"\D", "", doc or "")
    if pj and len(d) == 14:
        return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"
    if not pj and len(d) == 11:
        return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
    return doc or ""


def _caminho():
    return base_saida() / ARQ_REG


def listar() -> list:
    try:
        return json.loads(_caminho().read_text(encoding="utf-8"))
    except Exception:
        return []


def _record(d: dict, url_pasta: str) -> dict:
    ents = d.get("entidades", [])
    pj = next((e for e in ents if e.get("tipo") == "PJ"), None)
    pf = (next((e for e in ents if "operador" in e.get("papel", "").lower()), None)
          or next((e for e in ents if e.get("tipo") == "PF"), None))
    cidade = next((f"{e.get('municipio', '')}/{e.get('uf', '')}".strip("/")
                   for e in ents if e.get("municipio") or e.get("uf")), "")
    obs = d.get("concl_texto", "")
    if d.get("recomendacoes"):
        obs += " Recomendações: " + "; ".join(d["recomendacoes"])
    return {
        "id": str(d.get("id_suporte", "") or ""),
        "franquia": (pj.get("nome") if pj else (pf.get("nome") if pf else d.get("titulo"))) or "—",
        "cnpj": _fmt(pj.get("documento", ""), True) if pj else "",
        "representante": pf.get("nome", "") if pf else "",
        "cpf": _fmt(pf.get("documento", ""), False) if pf else "",
        "cidade_uf": cidade, "risco": d.get("risco", ""), "link": url_pasta or "",
        "obs": obs, "data": datetime.now().strftime("%d/%m/%Y"),
    }


def registrar(d: dict, url_pasta: str = "") -> dict:
    """Cria/atualiza a DD no cadastro (chaveia pelo ID Suporte; senão CNPJ+CPF)."""
    rec = _record(d, url_pasta)
    regs = listar()
    idx = None
    for i, r in enumerate(regs):
        if rec["id"] and r.get("id") == rec["id"]:
            idx = i
            break
        if not rec["id"] and (rec["cnpj"] or rec["cpf"]) and (r.get("cnpj"), r.get("cpf")) == (rec["cnpj"], rec["cpf"]):
            idx = i
            break
    if idx is None:
        regs.append(rec)
    else:
        regs[idx] = rec
    try:
        _caminho().write_text(json.dumps(regs, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    return rec


# ---------------------------------------------------------------- página /controle
_ESTILO = """
body{font-family:'Segoe UI',Arial,sans-serif;color:#1a2332;margin:0;background:#f4f6f8}
header{background:#1a2b3c;color:#fff;padding:1rem 2rem;display:flex;justify-content:space-between;align-items:center}
header h1{margin:0;font-size:1.2rem}header a{color:#9fd0e8;font-size:.9rem;text-decoration:none}
main{max-width:1200px;margin:1.4rem auto;padding:0 1rem}
.resumo{display:flex;gap:.7rem;margin-bottom:1rem;flex-wrap:wrap}
.pill{background:#fff;border-radius:10px;padding:.5rem .9rem;box-shadow:0 1px 4px rgba(0,0,0,.07);font-size:.9rem}
.pill b{font-size:1.1rem}
table{border-collapse:collapse;width:100%;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.08)}
th,td{border:1px solid #e3e6ea;padding:.5rem .6rem;text-align:left;font-size:.85rem;vertical-align:top}
th{background:#0b4f6c;color:#fff;position:sticky;top:0}
tr:nth-child(even){background:#fafbfc}
.risco{font-weight:700;text-align:center;white-space:nowrap;border-radius:6px}
td a{color:#0b6;font-weight:600;text-decoration:none}
.obs{max-width:420px}
.busca{padding:.5rem .7rem;border:1px solid #ccc;border-radius:8px;font-size:.95rem;width:280px;margin-bottom:.8rem}
.btn{background:#1a7d3c;color:#fff;padding:.5rem 1rem;border-radius:8px;text-decoration:none;font-weight:600;font-size:.85rem}
.vazio{background:#fff;padding:2rem;text-align:center;border-radius:10px;color:#777}
"""


def pagina_html() -> str:
    regs = listar()
    n = len(regs)
    por_risco = {}
    for r in regs:
        por_risco[r.get("risco", "—")] = por_risco.get(r.get("risco", "—"), 0) + 1
    pills = f'<div class="pill">Total de DDs <b>{n}</b></div>'
    for risco in ("ALTO", "MÉDIO", "BAIXO"):
        if por_risco.get(risco):
            cor = _COR.get(risco, ("#333", "#eee"))[0]
            pills += f'<div class="pill" style="color:{cor}">{risco} <b>{por_risco[risco]}</b></div>'

    if not regs:
        corpo = '<div class="vazio">Nenhuma DD registrada ainda. Gere um parecer e a DD aparece aqui.</div>'
    else:
        linhas = ""
        for r in reversed(regs):  # mais recentes primeiro
            risco = (r.get("risco") or "").upper()
            cf, cb = _COR.get(risco, ("#333", "#eee"))
            link = f'<a href="{r["link"]}" target="_blank">abrir pasta ↗</a>' if r.get("link") else "—"
            linhas += (
                f'<tr><td>{r.get("id", "")}</td><td><b>{r.get("franquia", "")}</b></td>'
                f'<td>{r.get("cnpj", "")}</td><td>{r.get("representante", "")}</td><td>{r.get("cpf", "")}</td>'
                f'<td>{r.get("cidade_uf", "")}</td>'
                f'<td class="risco" style="color:{cf};background:{cb}">{r.get("risco", "")}</td>'
                f'<td>{link}</td><td class="obs">{r.get("obs", "")}</td><td>{r.get("data", "")}</td></tr>')
        corpo = (
            '<input class="busca" id="q" placeholder="🔎 Filtrar (nome, CNPJ, cidade, risco...)" onkeyup="filtra()">'
            '<table id="tab"><thead><tr><th>ID</th><th>Franquia</th><th>CNPJ</th><th>Representante/Operador</th>'
            '<th>CPF</th><th>Cidade/UF</th><th>Risco</th><th>Pasta</th><th>Observações</th><th>Data</th></tr></thead>'
            f'<tbody>{linhas}</tbody></table>'
            '<script>function filtra(){var q=document.getElementById("q").value.toLowerCase();'
            'document.querySelectorAll("#tab tbody tr").forEach(function(tr){'
            'tr.style.display = tr.innerText.toLowerCase().includes(q) ? "" : "none";});}</script>')

    return (f'<!doctype html><html lang="pt-br"><head><meta charset="utf-8">'
            f'<title>Controle de Due Diligences</title><style>{_ESTILO}</style></head><body>'
            f'<header><h1>📊 Controle de Due Diligences</h1>'
            f'<span><a href="/">← Voltar ao sistema</a> &nbsp; '
            f'<a href="/controle.xlsx" class="btn">⬇️ Exportar Excel</a></span></header>'
            f'<main><div class="resumo">{pills}</div>{corpo}</main></body></html>')


def exportar_xlsx() -> str:
    """Gera o Excel sob demanda (a partir do cadastro) e devolve o caminho."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    cols = ["ID Suporte", "Franquia", "CNPJ", "Representante/Operador", "CPF", "Cidade/UF",
            "Risco", "Link da DD", "Observações", "Data"]
    larg = [11, 34, 20, 30, 16, 16, 9, 38, 70, 12]
    wb = Workbook()
    ws = wb.active
    ws.title = "Due Diligences"
    for c, t in enumerate(cols, 1):
        cel = ws.cell(1, c, t)
        cel.font = Font(bold=True, color="FFFFFF")
        cel.fill = PatternFill("solid", fgColor="0B4F6C")
        cel.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.column_dimensions[get_column_letter(c)].width = larg[c - 1]
    ws.freeze_panes = "A2"
    for r in listar():
        ws.append([r.get("id", ""), r.get("franquia", ""), r.get("cnpj", ""), r.get("representante", ""),
                   r.get("cpf", ""), r.get("cidade_uf", ""), r.get("risco", ""), r.get("link", ""),
                   r.get("obs", ""), r.get("data", "")])
        if r.get("link"):
            cel = ws.cell(ws.max_row, 8)
            cel.value = "abrir pasta"
            cel.hyperlink = r["link"]
            cel.font = Font(color="0563C1", underline="single")
        ws.cell(ws.max_row, 9).alignment = Alignment(wrap_text=True, vertical="top")
    destino = base_saida() / "Controle de Due Diligence.xlsx"
    wb.save(str(destino))
    return str(destino)
