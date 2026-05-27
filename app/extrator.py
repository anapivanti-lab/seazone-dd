"""Extrai dados de documentos anexados (imagem OU PDF), grátis e local:

- PJ → Cartão CNPJ: pega o número do CNPJ e completa razão social, endereço, UF e
  município pela BrasilAPI (mais confiável do que ler o PDF inteiro).
- PF → Identidade (RG/CNH): OCR (português + inglês juntos, mais robusto) +
  heurística para CPF, RG, nome, nome da mãe/pai e data de nascimento.

Lê PDF de texto (pypdf) e PDF escaneado/foto (Tesseract, renderizando as páginas
com o PyMuPDF). É best-effort: o que não vier legível, você completa na tela.
"""
from __future__ import annotations

import datetime
import io
import re
from pathlib import Path

from .cnpj_dados import consultar as consultar_cnpj
from .ocr import _tesseract_cmd

IMG_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp", ".gif"}


def _ocr_imagem(img, lang: str = "por") -> str:
    cmd = _tesseract_cmd()
    if not cmd:
        return ""
    try:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = cmd
        try:
            return pytesseract.image_to_string(img, lang=lang)
        except Exception:
            return pytesseract.image_to_string(img)
    except Exception:
        return ""


def _ocr_de_pdf(caminho: str, langs=("por",)) -> str:
    """Renderiza cada página do PDF como imagem (PyMuPDF) e faz OCR em cada idioma
    pedido — pega dados que estão em IMAGEM dentro do PDF (CNH Digital, RG)."""
    try:
        import fitz  # PyMuPDF
        from PIL import Image
        doc = fitz.open(caminho)
        partes = []
        for page in doc:
            img = Image.open(io.BytesIO(page.get_pixmap(dpi=300).tobytes("png")))
            for lang in langs:
                partes.append(_ocr_imagem(img, lang))
        doc.close()
        return "\n".join(partes).strip()
    except Exception:
        return ""


def _texto_de_pdf(caminho: str, ocr: bool = False, langs=("por",)) -> str:
    texto = ""
    try:
        from pypdf import PdfReader
        r = PdfReader(caminho)
        texto = "\n".join((p.extract_text() or "") for p in r.pages)
    except Exception:
        texto = ""
    # OCR da imagem se pedido (identidade) ou se não veio texto útil. Em documentos
    # de identidade o texto do PDF é só o rodapé; os dados reais estão na imagem.
    if ocr or len(texto.strip()) < 40:
        ocr_txt = _ocr_de_pdf(caminho, langs=langs)
        if ocr_txt:
            texto = ocr_txt + "\n" + texto
    return texto


def _texto_documento(caminho: str, ocr: bool = False, langs=("por",)) -> str:
    ext = Path(caminho).suffix.lower()
    if ext == ".pdf":
        return _texto_de_pdf(caminho, ocr=ocr, langs=langs)
    if ext in IMG_EXT:
        try:
            from PIL import Image
            img = Image.open(caminho)
            return "\n".join(_ocr_imagem(img, lang) for lang in langs)
        except Exception:
            return ""
    return _texto_de_pdf(caminho, ocr=ocr, langs=langs)


def extrair_cartao_cnpj(caminho: str) -> dict:
    """Lê o Cartão CNPJ e devolve documento (CNPJ), razão social, endereço, UF e
    município (via BrasilAPI a partir do número encontrado)."""
    texto = _texto_documento(caminho)
    m = re.search(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}", texto)
    if not m:  # não achou no texto -> tenta OCR da imagem (cartão escaneado/foto)
        texto = _texto_documento(caminho, ocr=True)
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


def _limpar_nome(s: str) -> str:
    """Remove ruído de OCR no começo do nome (tokens curtos/minúsculos/com número)."""
    toks = (s or "").split()
    while toks and (len(toks[0]) <= 2 or toks[0].islower() or any(c.isdigit() for c in toks[0])):
        toks.pop(0)
    return " ".join(toks).strip()


def extrair_identidade(caminho: str) -> dict:
    """Lê RG/CNH e devolve CPF, RG, nome, nome da mãe/pai e data de nascimento.
    Faz OCR em português E inglês (mais robusto) — os dados ficam na imagem."""
    texto = _texto_documento(caminho, ocr=True, langs=("por", "eng"))
    linhas = [l.strip() for l in texto.splitlines() if l.strip()]
    plano = " ".join(texto.split())

    # CPF: só no formato com pontos/traço (evita pegar o nº de registro da CNH)
    cpfs = re.findall(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", plano)
    cpf = re.sub(r"\D", "", cpfs[0]) if cpfs else ""

    # RG / nº do documento de identidade
    rg = ""
    m = re.search(r"(?:REGISTRO GERAL|REG[.\s]*GERAL|\bRG\b|DOC[.\s/]*IDENTIDADE|IDENTIDADE)[^\d]{0,30}(\d[\d.\-]{5,12}\w?)",
                  texto, re.I)
    if m:
        rg = m.group(1).strip(" .-")

    # Data de nascimento: a data mais antiga plausível (>= 16 anos atrás).
    # Assim evita confundir com validade / 1ª habilitação / data de emissão.
    ano_max = datetime.date.today().year - 16
    cands = []
    for dd, mm, yy in re.findall(r"\b(\d{2})/(\d{2})/(\d{4})\b", plano):
        y, mth, d = int(yy), int(mm), int(dd)
        if 1920 <= y <= ano_max and 1 <= mth <= 12 and 1 <= d <= 31:
            cands.append((y, mth, d, f"{dd}/{mm}/{yy}"))
    mnasc = re.search(r"NASC\w*\D{0,20}(\d{2})/(\d{2})/(\d{4})", texto, re.I)
    if mnasc and 1920 <= int(mnasc.group(3)) <= ano_max:
        data_nascimento = f"{mnasc.group(1)}/{mnasc.group(2)}/{mnasc.group(3)}"
    elif cands:
        data_nascimento = sorted(cands)[0][3]  # ano mais antigo = nascimento
    else:
        data_nascimento = ""

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

    nome, nome_mae, nome_pai = _limpar_nome(nome), _limpar_nome(nome_mae), _limpar_nome(nome_pai)
    ok = bool(cpf or rg or nome or nome_mae or data_nascimento)
    out = {"ok": ok, "tipo": "PF", "documento": cpf, "nome": nome, "rg": rg,
           "nome_mae": nome_mae, "nome_pai": nome_pai, "data_nascimento": data_nascimento}
    if not ok:
        out["erro"] = "Não consegui ler o documento. Preencha os campos à mão."
    return out
