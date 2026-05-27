"""Leitura (OCR) de documento de identidade (RG/CNH) para pré-preencher RG,
nome da mãe e data de nascimento. Usa o Tesseract (gratuito). É best-effort:
a imagem precisa estar legível, e você confere/corrige o que vier.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path


def _tesseract_cmd():
    for c in (r"C:\Program Files\Tesseract-OCR\tesseract.exe",
              r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"):
        if Path(c).exists():
            return c
    return shutil.which("tesseract")


def ler(caminho_imagem: str) -> dict:
    cmd = _tesseract_cmd()
    if not cmd:
        return {"ok": False, "erro": "Leitor de imagem (Tesseract) ainda não instalado."}
    try:
        import pytesseract
        from PIL import Image
        pytesseract.pytesseract.tesseract_cmd = cmd
        img = Image.open(caminho_imagem)
        try:
            texto = pytesseract.image_to_string(img, lang="por")
        except Exception:
            texto = pytesseract.image_to_string(img)
    except Exception as e:
        return {"ok": False, "erro": f"Falha no OCR: {e}"}
    dados = _extrair(texto)
    dados["ok"] = True
    return dados


def _extrair(texto: str) -> dict:
    linhas = [l.strip() for l in texto.splitlines() if l.strip()]
    plano = " ".join(texto.split())

    rg = ""
    m = re.search(r"(?:REGISTRO GERAL|REG[.\s]*GERAL|RG)\D{0,15}(\d{1,2}\.?\d{3}\.?\d{3}-?\w?)", texto, re.I)
    if m:
        rg = m.group(1)

    datas = re.findall(r"\b\d{2}/\d{2}/\d{4}\b", plano)
    data_nascimento = datas[0] if datas else ""

    nome_mae = ""
    for i, l in enumerate(linhas):
        if re.search(r"filia", l, re.I):
            cand = [x for x in linhas[i + 1:i + 5] if re.search(r"[A-ZÀ-Ú]{3,}\s+[A-ZÀ-Ú]{3,}", x)]
            if len(cand) >= 2:
                nome_mae = cand[1]   # heurística: 2º nome da filiação = mãe
            elif cand:
                nome_mae = cand[0]
            break

    return {"rg": rg, "data_nascimento": data_nascimento, "nome_mae": nome_mae}
