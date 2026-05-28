"""Extrai dados de documentos anexados (imagem OU PDF), grátis e local:

- PJ → Cartão CNPJ: pega o número do CNPJ e completa razão social, endereço, UF e
  município pela BrasilAPI (mais confiável do que ler o PDF inteiro).
- PF → Identidade (RG/CNH): OCR em português + inglês e em dois modos de
  segmentação (o normal e o "texto esparso", que pega o NOME do titular na CNH) +
  heurística para CPF, RG, nome, nome da mãe/pai e data de nascimento.

Lê PDF de texto (pypdf) e PDF escaneado/foto (Tesseract, renderizando as páginas
com o PyMuPDF). É best-effort: o que não vier legível, você completa na tela.
"""
from __future__ import annotations

import datetime
import io
import re
import unicodedata
from pathlib import Path

from .cnpj_dados import consultar as consultar_cnpj
from .ocr import _tesseract_cmd

IMG_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp", ".gif"}

# passadas de OCR: (idioma, psm). psm 11 = "texto esparso" (pega o NOME na CNH).
PASSES_DOC = (("por", None),)                                   # Cartão CNPJ
PASSES_ID = (("por", None), ("eng", None), ("por", 11))          # identidade

# palavras de moldura da CNH/RG que NÃO são nome de pessoa
_BOILER = ("REPUBLICA", "FEDERATIVA", "BRASIL", "VALIDA", "TERRITORIO", "NACIONAL",
           "DEPARTAMENTO", "TRANSITO", "DETRAN", "DENATRAN", "CONTRAN", "HABILITACAO",
           "ASSINATURA", "PORTADOR", "IDENTIDADE", "EMISSOR", "REGISTRO", "VALIDADE",
           "NASCIMENTO", "OBSERVACOES", "SERPRO", "PERMISSAO", "CARTEIRA", "MOTORISTA",
           "DIGITAL", "DOCUMENTO", "FILIACAO", "ESTADUAL", "CONSULTA", "NUMERO",
           "MINISTERIO", "SECRETARIA", "REPUBLICA")


def _ocr_imagem(img, lang: str = "por", psm: int | None = None) -> str:
    cmd = _tesseract_cmd()
    if not cmd:
        return ""
    config = f"--psm {psm}" if psm else ""
    try:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = cmd
        try:
            return pytesseract.image_to_string(img, lang=lang, config=config)
        except Exception:
            return pytesseract.image_to_string(img)
    except Exception:
        return ""


def _ocr_de_pdf(caminho: str, passes=PASSES_DOC) -> str:
    """Renderiza cada página (PyMuPDF) e faz OCR em cada passada pedida."""
    try:
        import fitz  # PyMuPDF
        from PIL import Image
        doc = fitz.open(caminho)
        partes = []
        for page in doc:
            img = Image.open(io.BytesIO(page.get_pixmap(dpi=300).tobytes("png")))
            for lang, psm in passes:
                partes.append(_ocr_imagem(img, lang, psm))
        doc.close()
        return "\n".join(partes).strip()
    except Exception:
        return ""


def _texto_de_pdf(caminho: str, ocr: bool = False, passes=PASSES_DOC) -> str:
    texto = ""
    try:
        from pypdf import PdfReader
        r = PdfReader(caminho)
        texto = "\n".join((p.extract_text() or "") for p in r.pages)
    except Exception:
        texto = ""
    if ocr or len(texto.strip()) < 40:
        ocr_txt = _ocr_de_pdf(caminho, passes=passes)
        if ocr_txt:
            texto = ocr_txt + "\n" + texto
    return texto


def _texto_documento(caminho: str, ocr: bool = False, passes=PASSES_DOC) -> str:
    ext = Path(caminho).suffix.lower()
    if ext == ".pdf":
        return _texto_de_pdf(caminho, ocr=ocr, passes=passes)
    if ext in IMG_EXT:
        try:
            from PIL import Image
            img = Image.open(caminho)
            return "\n".join(_ocr_imagem(img, lang, psm) for lang, psm in passes)
        except Exception:
            return ""
    return _texto_de_pdf(caminho, ocr=ocr, passes=passes)


def _juntar_letras_espacadas(linha: str) -> str:
    """O PDF do Cartão CNPJ da Receita vem com cada letra separada por 1 espaço e
    palavras separadas por 2+ espaços. Ex.: 'M A D U R E I R A' -> 'MADUREIRA',
    'R  M A R I A' -> 'R MARIA'. Em linhas que já vêm normais (ex.: 'NOME
    EMPRESARIAL'), não altera nada."""
    blocos = re.split(r" {2,}", linha.strip())
    saida = []
    for b in blocos:
        toks = b.split(" ")
        if len(toks) > 1 and all(len(t) == 1 for t in toks):
            saida.append("".join(toks))
        else:
            saida.append(b)
    return " ".join(saida).strip()


def _normalizar_cartao(texto: str) -> str:
    """Aplica _juntar_letras_espacadas linha a linha. Idempotente: linhas já normais
    passam intactas. Necessário porque o pypdf extrai o cartão da Receita com cada
    letra/dígito separada por espaço."""
    return "\n".join(_juntar_letras_espacadas(l) for l in texto.splitlines())


def _ler_cartao_do_pdf(texto: str) -> dict:
    """Fallback quando a BrasilAPI não tem o CNPJ (típico de empresa recém-aberta):
    lê razão social, logradouro, número, bairro, município, UF e CEP direto do
    texto do Cartão CNPJ da Receita."""
    linhas = [l for l in _normalizar_cartao(texto).splitlines() if l.strip()]

    def proximo_valor(*rotulos: str) -> str:
        rx = re.compile("|".join(rotulos), re.I)
        for i, l in enumerate(linhas):
            if rx.fullmatch(l):
                for prox in linhas[i + 1:i + 3]:
                    v = prox.strip(" *").strip()
                    if v and v != "*":
                        return v
                break
        return ""

    razao = proximo_valor(r"NOME\s+EMPRESARIAL")
    logradouro = proximo_valor(r"LOGRADOURO")
    numero = proximo_valor(r"N.MERO")  # NÚMERO (do endereço; rótulo curto)
    bairro = proximo_valor(r"BAIRRO[/\\]DISTRIT\s*O")
    cep = proximo_valor(r"CEP")
    municipio = proximo_valor(r"MUNIC.PIO")
    uf = proximo_valor(r"UF")

    endereco = ", ".join(filter(None, [
        f"{logradouro} {numero}".strip() if (logradouro or numero) else "",
        bairro,
        f"{municipio}/{uf}".strip("/") if (municipio or uf) else "",
        f"CEP {cep}" if cep else "",
    ]))
    return {"razao_social": razao, "uf": uf, "municipio": municipio, "endereco": endereco}


def extrair_cartao_cnpj(caminho: str) -> dict:
    """Lê o Cartão CNPJ e devolve documento (CNPJ), razão social, endereço, UF e
    município. Tenta a BrasilAPI primeiro (mais limpo); se ela não tem o CNPJ
    (empresa recém-aberta, fora do ar), lê os dados do próprio PDF do cartão."""
    texto = _normalizar_cartao(_texto_documento(caminho))
    m = re.search(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}", texto)
    if not m:  # não achou no texto -> tenta OCR da imagem (cartão escaneado/foto)
        texto = _normalizar_cartao(_texto_documento(caminho, ocr=True))
        m = re.search(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}", texto)
    cnpj = re.sub(r"\D", "", m.group(0)) if m else ""
    out = {"ok": bool(cnpj), "tipo": "PJ", "documento": cnpj,
           "nome": "", "uf": "", "municipio": "", "endereco": ""}
    if not cnpj:
        out["erro"] = "Não consegui ler o CNPJ do cartão. Digite o CNPJ à mão."
        return out

    dados = consultar_cnpj(cnpj)
    if dados:
        out.update(nome=dados.get("razao_social", ""), uf=dados.get("uf", ""),
                   municipio=dados.get("municipio", ""), endereco=dados.get("endereco", ""))

    # Fallback: lê do próprio cartão o que a BrasilAPI não trouxe (CNPJ recém-aberto)
    if not (out["nome"] and out["endereco"]):
        do_pdf = _ler_cartao_do_pdf(texto)
        out["nome"] = out["nome"] or do_pdf["razao_social"]
        out["uf"] = out["uf"] or do_pdf["uf"]
        out["municipio"] = out["municipio"] or do_pdf["municipio"]
        out["endereco"] = out["endereco"] or do_pdf["endereco"]
    return out


def _limpar_nome(s: str) -> str:
    """Remove ruído de OCR no começo do nome (tokens curtos/minúsculos/com número)."""
    toks = (s or "").split()
    while toks and (len(toks[0]) <= 2 or toks[0].islower() or any(c.isdigit() for c in toks[0])):
        toks.pop(0)
    return " ".join(toks).strip()


def _cmp(s: str) -> str:
    s = "".join(c for c in unicodedata.normalize("NFKD", s or "") if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.upper()).strip()


def cpf_valido(cpf: str) -> bool:
    """Confere os dígitos verificadores do CPF (pega erro de leitura do OCR)."""
    c = re.sub(r"\D", "", cpf or "")
    if len(c) != 11 or len(set(c)) == 1:
        return False
    for i in (9, 10):
        soma = sum(int(c[n]) * ((i + 1) - n) for n in range(i))
        if (soma * 10 % 11 % 10) != int(c[i]):
            return False
    return True


def _imagens_extra(caminho: str):
    """Imagens para o 'triple check' do CPF: imagem(ns) embutida(s) em alta resolução
    + render em 400 dpi (PDF), ou a própria imagem + ampliada (arquivo de imagem)."""
    ext = Path(caminho).suffix.lower()
    imgs = []
    try:
        from PIL import Image
        if ext == ".pdf":
            import fitz
            doc = fitz.open(caminho)
            embut = []
            for img in doc.get_page_images(0):
                try:
                    base = doc.extract_image(img[0])
                    im = Image.open(io.BytesIO(base["image"]))
                    if im.width >= 300 and im.height >= 200:
                        embut.append(im)
                except Exception:
                    pass
            embut.sort(key=lambda im: im.width * im.height, reverse=True)
            for im in embut[:1]:  # a maior (frente da CNH/RG)
                imgs.append(im)
                imgs.append(im.resize((im.width * 2, im.height * 2)))
            imgs.append(Image.open(io.BytesIO(doc[0].get_pixmap(dpi=400).tobytes("png"))))
            doc.close()
        elif ext in IMG_EXT:
            im = Image.open(caminho)
            imgs.append(im)
            imgs.append(im.resize((im.width * 2, im.height * 2)))
    except Exception:
        pass
    return imgs


def _coletar_cpfs(texto: str, cont: dict) -> None:
    for c in re.findall(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}", texto) + re.findall(r"(?<!\d)\d{11}(?!\d)", texto):
        d = re.sub(r"\D", "", c)
        if len(d) == 11:
            cont[d] = cont.get(d, 0) + 1


def melhor_cpf(caminho: str, texto_base: str = "") -> str:
    """'Triple check' do CPF: junta os candidatos do texto + várias passadas de OCR e
    escolhe o que PASSA na validação e aparece mais vezes (votação). '' se nenhum valida."""
    cont: dict = {}
    _coletar_cpfs(texto_base, cont)
    for im in _imagens_extra(caminho):
        for lang, psm in (("por", 6), ("eng", 6)):
            _coletar_cpfs(_ocr_imagem(im, lang, psm), cont)
    validos = {d: n for d, n in cont.items() if cpf_valido(d)}
    return max(validos, key=validos.get) if validos else ""


def _eh_nome(s: str) -> bool:
    return bool(re.search(r"[A-ZÀ-Ú]{3,}\s+[A-ZÀ-Ú]{2,}", s))


def _achar_nome_titular(linhas, mae, pai) -> str:
    """O nome do titular = o nome de pessoa que NÃO é moldura do documento nem o
    pai/mãe. Pega o mais completo (mais palavras)."""
    excl = [_cmp(mae), _cmp(pai)]
    cands = []
    for l in linhas:
        nome = _limpar_nome(l)
        if not _eh_nome(nome) or any(c.isdigit() for c in nome):
            continue
        c = _cmp(nome)
        if any(b in c for b in _BOILER):
            continue
        if any(e and (c in e or e in c) for e in excl):  # é o pai/mãe
            continue
        cands.append(nome)
    if not cands:
        return ""
    return max(cands, key=lambda n: (len(n.split()), len(n)))


def extrair_identidade(caminho: str) -> dict:
    """Lê RG/CNH e devolve CPF, RG, nome, nome da mãe/pai e data de nascimento."""
    texto = _texto_documento(caminho, ocr=True, passes=PASSES_ID)
    linhas = [l.strip() for l in texto.splitlines() if l.strip()]
    plano = " ".join(texto.split())

    # CPF: "triple check" — junta candidatos do texto + várias passadas de OCR e
    # escolhe o que passa na validação e mais se repete (corrige erro de leitura).
    cpf = melhor_cpf(caminho, texto)

    rg = ""
    m = re.search(r"(?:REGISTRO GERAL|REG[.\s]*GERAL|\bRG\b|DOC[.\s/]*IDENTIDADE|IDENTIDADE)[^\d]{0,30}(\d[\d.\-]{5,12}\w?)",
                  texto, re.I)
    if m:
        rg = m.group(1).strip(" .-")

    # Órgão expedidor (ex.: SSP/SP, SEJUSP/MT) — costuma vir logo após o nº do RG
    orgao = ""
    mo = re.search(r"\b\d{6,9}\s+([A-ZÀ-Ú]{2,8})(?:[\s/\-]+([A-Z]{2})\b)?", texto)
    if mo and _cmp(mo.group(1)) not in _BOILER:
        orgao = mo.group(1) + ("/" + mo.group(2) if mo.group(2) else "")

    # Data de nascimento: a data mais antiga plausível (>= 16 anos atrás)
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
        data_nascimento = sorted(cands)[0][3]
    else:
        data_nascimento = ""

    # Filiação (pai/mãe)
    nome_mae = nome_pai = ""
    for i, l in enumerate(linhas):
        if re.search(r"filia", l, re.I):
            cand = [x for x in linhas[i + 1:i + 6] if _eh_nome(x)]
            if len(cand) >= 2:
                nome_pai, nome_mae = cand[0], cand[1]
            elif cand:
                nome_mae = cand[0]
            break
    nome_mae, nome_pai = _limpar_nome(nome_mae), _limpar_nome(nome_pai)

    # Nome do titular: tenta o rótulo "NOME"; senão, o nome que não é pai/mãe/moldura
    nome = ""
    for i, l in enumerate(linhas):
        if re.search(r"\bNOME\b", l, re.I) and not re.search(r"filia|m[ãa]e|pai|social", l, re.I):
            c = [x for x in linhas[i + 1:i + 3] if _eh_nome(x)]
            if c:
                nome = _limpar_nome(c[0])
                break
    if not nome:
        nome = _achar_nome_titular(linhas, nome_mae, nome_pai)

    ok = bool(cpf or rg or nome or nome_mae or data_nascimento)
    out = {"ok": ok, "tipo": "PF", "documento": cpf, "cpf_lido": bool(cpf), "nome": nome,
           "rg": rg, "nome_mae": nome_mae, "nome_pai": nome_pai,
           "data_nascimento": data_nascimento, "orgao_expedidor": orgao}
    if not ok:
        out["erro"] = "Não consegui ler o documento. Preencha os campos à mão."
    return out


def _extrair_pj_do_texto(texto: str, caminho: str) -> dict:
    """Tenta achar CNPJ no texto e, se achar, consulta a BrasilAPI; senão lê do PDF."""
    t = _normalizar_cartao(texto)
    m = re.search(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}", t)
    if not m:
        return {}
    cnpj = re.sub(r"\D", "", m.group(0))
    out = {"documento_pj": cnpj}
    dados = consultar_cnpj(cnpj)
    if dados:
        out.update(nome_pj=dados.get("razao_social", ""), uf=dados.get("uf", ""),
                   municipio=dados.get("municipio", ""), endereco=dados.get("endereco", ""))
    if not (out.get("nome_pj") and out.get("endereco")):
        do_pdf = _ler_cartao_do_pdf(t)
        out["nome_pj"] = out.get("nome_pj") or do_pdf["razao_social"]
        out["uf"] = out.get("uf") or do_pdf["uf"]
        out["municipio"] = out.get("municipio") or do_pdf["municipio"]
        out["endereco"] = out.get("endereco") or do_pdf["endereco"]
    return {k: v for k, v in out.items() if v}


def _extrair_pf_do_texto(texto: str, caminho: str) -> dict:
    """Tenta achar dados de PF (CPF, nome, RG, mãe, nascimento) no texto."""
    linhas = [l.strip() for l in texto.splitlines() if l.strip()]
    plano = " ".join(texto.split())
    cpf = melhor_cpf(caminho, texto)

    rg = ""
    m = re.search(r"(?:REGISTRO GERAL|REG[.\s]*GERAL|\bRG\b|DOC[.\s/]*IDENTIDADE|IDENTIDADE)[^\d]{0,30}(\d[\d.\-]{5,12}\w?)",
                  texto, re.I)
    if m:
        rg = m.group(1).strip(" .-")

    orgao = ""
    mo = re.search(r"\b\d{6,9}\s+([A-ZÀ-Ú]{2,8})(?:[\s/\-]+([A-Z]{2})\b)?", texto)
    if mo and _cmp(mo.group(1)) not in _BOILER:
        orgao = mo.group(1) + ("/" + mo.group(2) if mo.group(2) else "")

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
        data_nascimento = sorted(cands)[0][3]
    else:
        data_nascimento = ""

    nome_mae = nome_pai = ""
    for i, l in enumerate(linhas):
        if re.search(r"filia", l, re.I):
            cand = [x for x in linhas[i + 1:i + 6] if _eh_nome(x)]
            if len(cand) >= 2:
                nome_pai, nome_mae = cand[0], cand[1]
            elif cand:
                nome_mae = cand[0]
            break
    # Fallback: "Nome da Mãe: FULANA"
    if not nome_mae:
        m2 = re.search(r"m[aã]e[:\s]+([A-ZÀ-Ú][A-ZÀ-Úa-zà-ú ]{4,})", texto, re.I)
        if m2:
            nome_mae = m2.group(1).strip()
    nome_mae, nome_pai = _limpar_nome(nome_mae), _limpar_nome(nome_pai)

    nome = ""
    for i, l in enumerate(linhas):
        if re.search(r"\bNOME\b", l, re.I) and not re.search(r"filia|m[ãa]e|pai|social", l, re.I):
            c = [x for x in linhas[i + 1:i + 3] if _eh_nome(x)]
            if c:
                nome = _limpar_nome(c[0])
                break
    if not nome:
        nome = _achar_nome_titular(linhas, nome_mae, nome_pai)

    out = {}
    if cpf: out["documento_pf"] = cpf
    if nome: out["nome_pf"] = nome
    if rg: out["rg"] = rg
    if nome_mae: out["nome_mae"] = nome_mae
    if nome_pai: out["nome_pai"] = nome_pai
    if data_nascimento: out["data_nascimento"] = data_nascimento
    if orgao: out["orgao_expedidor"] = orgao
    return out


def extrair_tudo(caminho: str) -> dict:
    """Lê QUALQUER documento (imagem ou PDF) e tenta extrair tudo — PJ e PF — sem
    depender do usuário dizer o tipo. Devolve um dict com os campos que conseguiu.

    O texto é lido UMA vez com OCR forte (português + inglês + texto esparso) e
    aplicado nas duas extrações. Funciona com Cartão CNPJ, RG, CNH, contrato
    social, comprovantes, certidões — qualquer documento."""
    texto = _texto_documento(caminho, ocr=True, passes=PASSES_ID)
    pj = _extrair_pj_do_texto(texto, caminho)
    pf = _extrair_pf_do_texto(texto, caminho)
    achou = bool(pj or pf)
    out = {"ok": achou, **pj, **pf}
    if not achou:
        out["erro"] = "Não consegui extrair nada deste documento. Tente outro arquivo ou preencha à mão."
    return out


def mesclar(resultados: list[dict]) -> dict:
    """Junta vários resultados de extrair_tudo() em um único dict. Primeiro valor
    não-vazio vence (ex.: Cartão CNPJ traz CNPJ+endereço+razão social; RG traz
    CPF+nome+mãe+nascimento — combinados dão a DD completa)."""
    final: dict = {"ok": False}
    for r in resultados or []:
        if not isinstance(r, dict):
            continue
        if r.get("ok"):
            final["ok"] = True
        for k, v in r.items():
            if k in ("ok", "erro", "tipo"):
                continue
            if v and not final.get(k):
                final[k] = v
    # Compatibilidade com a UI antiga: tipo+documento+nome principais
    if final.get("documento_pj") and not final.get("documento"):
        final["documento"] = final["documento_pj"]
        final["nome"] = final.get("nome_pj") or final.get("nome", "")
        final["tipo"] = "PJ"
    elif final.get("documento_pf") and not final.get("documento"):
        final["documento"] = final["documento_pf"]
        final["nome"] = final.get("nome_pf") or final.get("nome", "")
        final["tipo"] = "PF"
    return final
