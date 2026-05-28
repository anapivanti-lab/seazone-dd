"""Planilha de Controle das Due Diligences (Excel editável). A cada parecer
gerado, o sistema preenche/atualiza automaticamente uma linha na planilha mestre
(uma por DD), salva na pasta das Franquias do Drive. Você pode abrir e editar no
Excel normalmente.
"""
from __future__ import annotations

import re
from datetime import datetime

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .config import base_saida

ARQ = "Controle de Due Diligence.xlsx"
COLS = ["ID Suporte", "Franquia", "CNPJ", "Representante legal / Operador", "CPF",
        "Cidade/UF", "Risco", "Link da DD (Drive)", "Observações", "Data"]
LARGURAS = [11, 34, 20, 30, 16, 16, 9, 40, 70, 12]
_RISCO_FILL = {"ALTO": "F8D7DA", "MÉDIO": "FFF3CD", "BAIXO": "D4EDDA"}
_RISCO_FONT = {"ALTO": "C0392B", "MÉDIO": "B8860B", "BAIXO": "1A7D3C"}
_AZUL = "0B4F6C"


def _fmt(doc: str, pj: bool) -> str:
    d = re.sub(r"\D", "", doc or "")
    if pj and len(d) == 14:
        return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"
    if not pj and len(d) == 11:
        return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
    return doc or ""


def _linha(d: dict, url_pasta: str) -> list:
    ents = d.get("entidades", [])
    pj = next((e for e in ents if e.get("tipo") == "PJ"), None)
    pf = (next((e for e in ents if "operador" in e.get("papel", "").lower()), None)
          or next((e for e in ents if e.get("tipo") == "PF"), None))
    franquia = (pj.get("nome") if pj else (pf.get("nome") if pf else d.get("titulo"))) or "—"
    cnpj = _fmt(pj.get("documento", ""), True) if pj else ""
    rep = pf.get("nome", "") if pf else ""
    cpf = _fmt(pf.get("documento", ""), False) if pf else ""
    cidade = next((f"{e.get('municipio', '')}/{e.get('uf', '')}".strip("/")
                   for e in ents if e.get("municipio") or e.get("uf")), "")
    obs = d.get("concl_texto", "")
    if d.get("recomendacoes"):
        obs += " Recomendações: " + "; ".join(d["recomendacoes"])
    return [d.get("id_suporte", ""), franquia, cnpj, rep, cpf, cidade,
            d.get("risco", ""), url_pasta or "", obs, datetime.now().strftime("%d/%m/%Y")]


def _estilo_cabecalho(ws):
    for c, titulo in enumerate(COLS, 1):
        cel = ws.cell(1, c, titulo)
        cel.font = Font(bold=True, color="FFFFFF", size=11)
        cel.fill = PatternFill("solid", fgColor=_AZUL)
        cel.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.column_dimensions[get_column_letter(c)].width = LARGURAS[c - 1]
    ws.row_dimensions[1].height = 28
    ws.freeze_panes = "A2"


def registrar(d: dict, url_pasta: str = "") -> str:
    """Cria/atualiza a linha desta DD na planilha de controle. Chaveia pelo ID
    Suporte (ou CNPJ+CPF) — re-gerar o parecer atualiza a mesma linha."""
    caminho = base_saida() / ARQ
    if caminho.exists():
        wb = load_workbook(caminho)
        ws = wb.active
    else:
        wb = Workbook()
        ws = wb.active
        ws.title = "Due Diligences"
        _estilo_cabecalho(ws)

    linha = _linha(d, url_pasta)
    id_s = str(linha[0] or "")
    chave_cnpj_cpf = (linha[2], linha[4])

    alvo = None
    for r in range(2, ws.max_row + 1):
        if id_s and str(ws.cell(r, 1).value or "") == id_s:
            alvo = r
            break
        if not id_s and (ws.cell(r, 3).value, ws.cell(r, 5).value) == chave_cnpj_cpf and any(chave_cnpj_cpf):
            alvo = r
            break
    if alvo is None:
        alvo = ws.max_row + 1

    for c, val in enumerate(linha, 1):
        ws.cell(alvo, c, val)
    # link clicável
    if url_pasta:
        cel = ws.cell(alvo, 8)
        cel.value = "abrir pasta"
        cel.hyperlink = url_pasta
        cel.font = Font(color="0563C1", underline="single")
    # risco colorido
    risco = (linha[6] or "").upper()
    rc = ws.cell(alvo, 7)
    rc.font = Font(bold=True, color=_RISCO_FONT.get(risco, "333333"))
    if risco in _RISCO_FILL:
        rc.fill = PatternFill("solid", fgColor=_RISCO_FILL[risco])
    rc.alignment = Alignment(horizontal="center", vertical="center")
    ws.cell(alvo, 9).alignment = Alignment(wrap_text=True, vertical="top")

    wb.save(caminho)
    return str(caminho)
