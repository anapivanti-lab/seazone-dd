"""Extrai dados de documentos anexados (imagem OU PDF), grátis e local:

- PJ → Cartão CNPJ: pega o número do CNPJ e completa razão social, endereço, UF e
  município pela BrasilAPI (mais confiável do que ler o PDF inteiro).
- PF → Identidade (RG/CNH): OCR + heurística para CPF, RG, nome, nome da mãe/pai e
  data de nascimento.

Lê tanto PDF de texto (pypdf) quanto PDF escaneado/foto (Tesseract, renderizando as
páginas com o PyMuPDF). É best-effort: o que não vier legível, você completa na tela.
"""
from __future__ import annotations

import io
import re
from pathlib import Path

from .cnpj_dados import consultar as consultar_cnpj
from .ocr import _tesseract_cmd

IMG_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp", ".gif"}


def _ocr_imagem(img) -> str:
    cmd = _tesseract_cmd()
    if not cmd:
        return ""
    try:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = cmd
        try:
            return pytesseract.image_to_string(img, lang="por")
        except Exception:
            return pytesseract.image_to_string(img)
    except Exception:
        return ""


def _texto_de_pdf(caminho: str) -> str:
    # 1) tenta extrair o texto direto (Cartão CNPJ costuma ser PDF de texto)
    texto = ""
    try:
        from pypdf import PdfReader
        r = PdfReader(caminho)
        texto = "\n".join((p.extract_text() or "") for p in r.pages)
    except Exception:
        texto = ""
    if len(texto.strip()) >= 40:
        return texto
    # 2) PDF escaneado/foto -> renderiza as páginas e faz OCR
    try:
        import fitz  # PyMuPDF
        from PIL import Image
        doc = fitz.open(caminho)
        partes = []
        for page in doc:
            pix = page.get_pixmap(dpi=300)
            partes.append(_ocr_imagem(Image.open(io.BytesIO(pix.tobytes("png")))))
        doc.close()
        return "\n".join(partes).strip() or texto
    except Exception:
        return texto


def _texto_documento(caminho: str) -> str:
    ext = Path(caminho).suffix.lower()
    if ext == ".pdf":
        return _texto_de_pdf(caminho)
    if ext in IMG_EXT:
        try:
            from PIL import Image
            return _ocr_imagem(Image.open(caminho))
        except Exception:
            return ""
    return _texto_de_pdf(caminho)  # desconhecido: tenta como PDF


def extrair_cartao_cnpj(caminho: str) -> dict:
    """Lê o Cartão CNPJ e devolve documento (CNPJ), razão social, endereço, UF e
    município (via BrasilAPI a partir do número encontrado)."""
    texto = _texto_documento(caminho)
    m = re.search(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}", texto)
    cnpj = re.sub(r"\D", "", m.group(0)) if m else ""
    out = {"ok": bool(cnpj), "tipo": "PJ", "documento": cnpj,
           "nome": "", "uf": "", "municipio": "", "endereco": ""}
    if cnpj:
        dados = consultar_cnpj(cnpj)
        if dados:
            out.update(nome=dados.get("razao_social", ""), uf=dados.get("uf", ""),
                       municipio=dados.get("municipio", ""), endereco=dados.get("endereco", ""))
    else:
        out["erro"] = "Não consegui ler o CNPJ do cartão. Digite o CNPJ à mão."
    return out


def extrair_identidade(caminho: str) -> dict:
    """Lê RG/CNH e devolve CPF, RG, nome, nome da mãe/pai e data de nascimento."""
    texto = _texto_documento(caminho)
    linhas = [l.strip() for l in texto.splitlines() if l.strip()]
    plano = " ".join(texto.split())

    cpf = ""
    m = re.search(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b", plano)
    if m:
        cpf = re.sub(r"\D", "", m.group(0))

    rg = ""
    m = re.search(r"(?:REGISTRO GERAL|REG[.\s]*GERAL|\bRG\b|IDENTIDADE)\D{0,15}(\d{1,2}\.?\d{3}\.?\d{3}-?\w?)",
                  texto, re.I)
    if m:
        rg = m.group(1)

    mnasc = re.search(r"NASC\w*\D{0,20}(\d{2}/\d{2}/\d{4})", texto, re.I)
    datas = re.findall(r"\b\d{2}/\d{2}/\d{4}\b", plano)
    data_nascimento = mnasc.group(1) if mnasc else (datas[0] if datas else "")

    def _eh_nome(s):
        return bool(re.search(r"[A-ZÀ-Ú]{3,}\s+[A-ZÀ-Ú]{2,}", s))

    nome = ""
    for i, l in enumerate(linhas):
        if re.search(r"\bNOME\b", l, re.I) and not re.search(r"filia|m[ãa]e|pai|social", l, re.I):
            cand = [x for x in linhas[i + 1:i + 3] if _eh_nome(x)]
            if cand:
                nome = cand[0]
                break

    nome_mae = nome_pai = ""
    for i, l in enumerate(linhas):
        if re.search(r"filia", l, re.I):
            cand = [x for x in linhas[i + 1:i + 6] if _eh_nome(x)]
            if len(cand) >= 2:
                nome_pai, nome_mae = cand[0], cand[1]  # heurística: 1º pai, 2º mãe
            elif cand:
                nome_mae = cand[0]
            break

    ok = bool(cpf or rg or nome or nome_mae or data_nascimento)
    out = {"ok": ok, "tipo": "PF", "documento": cpf, "nome": nome, "rg": rg,
           "nome_mae": nome_mae, "nome_pai": nome_pai, "data_nascimento": data_nascimento}
    if not ok:
        out["erro"] = "Não consegui ler o documento. Preencha os campos à mão."
    return out
