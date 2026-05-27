"""Leitor de processos judiciais: lê o PDF (eproc/PJe e similares) e monta um
RELATÓRIO COMPLETO — classe, objeto/assunto, partes (com nomes e documentos),
papel da pessoa da DD, fatos, andamentos, situação atual, sentença, valores e
riscos. 100% local e gratuito (sem IA paga); best-effort conforme o tribunal.
"""
from __future__ import annotations

import re

from pypdf import PdfReader

_RISCOS = {
    "Criminal": ["criminal", "ação penal", " penal ", "estelionato", "furto", "roubo",
                 "apropriação indébita", "lavagem de dinheiro", "homicídio", "tráfico"],
    "Fraude": ["fraude", "fraudulent", "falsidade", "falsific", "simulação", "procuração falsa"],
    "Execução": ["execução", "exequente", "executado", "penhora", "execução fiscal", "cumprimento de sentença"],
    "Trabalhista": ["reclamante", "reclamada", "trabalhista", "verbas rescisórias", "vínculo empregatício"],
    "Cível/Cobrança": ["indenização", "danos morais", "cobrança", "monitória", "rescisão contratual", "busca e apreensão"],
}


def _extrair_texto(caminho: str) -> str:
    try:
        r = PdfReader(caminho)
        return "\n".join((p.extract_text() or "") for p in r.pages)
    except Exception:
        return ""


def _num(v: str) -> float:
    n = re.sub(r"[^\d,]", "", v).replace(".", "").replace(",", ".") if "," in v else re.sub(r"[^\d.]", "", v)
    try:
        return float(n)
    except Exception:
        return 0.0


def _valor_apos(linhas, *rotulos) -> str:
    """Valor que vem depois de um rótulo (na mesma linha após ':' ou na linha seguinte)."""
    for i, l in enumerate(linhas):
        for rot in rotulos:
            m = re.match(re.escape(rot) + r"\s*:?\s*(.*)$", l, re.I)
            if m:
                if m.group(1).strip():
                    return m.group(1).strip()
                # valor na próxima linha não-vazia
                for j in range(i + 1, min(i + 3, len(linhas))):
                    if linhas[j].strip():
                        return linhas[j].strip()
    return ""


_LABELS = (r"Entidade|Pessoa F[íi]sica|Pessoa Jur[íi]dica|Autoridade|AUTOR(?:A|ES)?|"
           r"R[ÉE](?:US?)?|REQUERENTES?|REQUERID[OA]S?|EXEQUENTES?|EXECUTAD[OA]S?|"
           r"RECLAMANTES?|RECLAMAD[OA]S?|INTERESSAD[OA]S?|V[ÍI]TIMAS?|REPRESENTANTES?")


def _partes(texto):
    """Extrai as partes: o NOME é a linha logo acima do documento; o documento pode
    estar quebrado em 2 linhas (junta) — robusto para o layout do eproc/PJe."""
    linhas = texto.splitlines()
    out, vistos = [], set()
    n = len(linhas)
    for i, l in enumerate(linhas):
        if not re.search(r"\(\s*\d", l):  # linha que abre um documento "(12..."
            continue
        docraw = l if ")" in l else (l + " " + (linhas[i + 1] if i + 1 < n else ""))
        md = re.search(r"\(\s*([\d][\d./\-\s]{9,22}[\d\w])\s*\)", docraw)
        if not md:
            continue
        doc = re.sub(r"\s", "", md.group(1))
        if len(re.sub(r"\D", "", doc)) not in (11, 14) or doc in vistos:
            continue
        nome = ""
        for j in range(i - 1, max(-1, i - 5), -1):  # nome = linha de cima que pareça nome
            c = linhas[j].strip(" .-")
            if not c or "(" in c:
                continue
            if re.match(r"^(?:" + _LABELS + r"|Partes e Representantes|Informa)\b", c, re.I):
                continue
            if re.search(r"[A-ZÀ-Ú]{2,}", c):
                nome = re.sub(r"\s+", " ", c).strip(" .-")
                break
        if len(nome) < 4:
            continue
        tm = re.search(r"(Pessoa F[íi]sica|Pessoa Jur[íi]dica|Entidade|Autoridade)",
                       " ".join(linhas[i:i + 4]), re.I)
        vistos.add(doc)
        out.append({"nome": nome, "doc": doc, "tipo": tm.group(1) if tm else ""})
    return out


def _papel_dd(low, ctx, partes):
    if not ctx:
        return ""
    doc = re.sub(r"\D", "", getattr(ctx, "documento", "") or "")
    nome = (getattr(ctx, "nome", "") or "").strip()
    primeiro = nome.split()[0] if nome else ""
    achou = None
    for p in partes:
        if doc and re.sub(r"\D", "", p["doc"]) == doc:
            achou = p
            break
        if primeiro and len(primeiro) > 2 and primeiro.lower() in p["nome"].lower():
            achou = p
    if not achou:
        return ("Não localizei a pessoa da DD entre as partes deste processo — "
                "confira se o processo realmente se refere a ela.")
    tem_mp = any("MINIST" in p["nome"].upper() for p in partes)
    pl = primeiro.lower()
    polo = ""
    if pl and re.search(r"(?:contra|em face de|denunciad[oa]|réu|requerid[oa]|executad[oa])[^.]{0,120}" + re.escape(pl), low):
        polo = "polo passivo (réu / requerido / executado)"
    elif tem_mp and "ísica" in achou["tipo"]:
        polo = "polo passivo (réu em ação penal)"
    elif pl and re.search(re.escape(pl) + r"[^.]{0,80}(?:autor|requerente|exequente|reclamante|ajuíz|promove)", low):
        polo = "polo ativo (autor / exequente)"
    return f"{achou['nome']} (doc. {achou['doc']}) figura no {polo or 'processo'}."


def _fatos(texto):
    """Trecho narrativo (denúncia / petição inicial) — o que aconteceu."""
    for marco in ("DOS FATOS", "DENÚNCIA", "DENUNCIA", "Narra ", "Consta dos autos", "Trata-se"):
        i = texto.find(marco)
        if i != -1:
            t = re.sub(r"\s+", " ", texto[i:i + 1100]).strip()
            return t[:900] + ("…" if len(t) > 900 else "")
    return ""


def _andamentos(texto):
    """Lista de movimentações: (data, descrição), do PDF do eproc/PJe."""
    eventos = []
    for m in re.finditer(r"Sequ[êe]ncia Evento:\s*(.+?)(\d{2}/\d{2}/\d{4})\s+\d{2}:\d{2}:\d{2}", texto, re.S):
        desc = re.sub(r"\s+", " ", m.group(1)).strip()
        if 3 < len(desc) < 200:
            eventos.append({"data": m.group(2), "descricao": desc})
    return eventos


def _sentenca(texto):
    low = texto.lower()
    for kw, rotulo in [("julgo procedente", "Procedente"), ("julgo improcedente", "Improcedente"),
                       ("julgo parcialmente procedente", "Parcialmente procedente"),
                       ("condeno", "Condenação"), ("absolvo", "Absolvição"),
                       ("extingo a punibilidade", "Extinção da punibilidade"),
                       ("homologo", "Homologação (acordo)"), ("extinta a execução", "Execução extinta (quitada)")]:
        if kw in low:
            i = low.find(kw)
            trecho = re.sub(r"\s+", " ", texto[max(0, i - 20):i + 300]).strip()
            return {"resultado": rotulo, "trecho": trecho}
    return None


def analisar(caminho: str, ctx=None) -> dict:
    texto = _extrair_texto(caminho)
    linhas = [l.strip() for l in texto.splitlines() if l.strip()]
    plano = " ".join(texto.split())
    low = plano.lower()

    nproc = re.search(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}", plano)
    valores = re.findall(r"R\$\s?[\d\.]{1,15},\d{2}", plano)
    nums = [_num(v) for v in valores]
    valor_maximo = max(nums) if nums else 0.0

    partes = _partes(texto)
    riscos = [cat for cat, kws in _RISCOS.items() if any(k in low for k in kws)]
    andamentos = _andamentos(texto)
    sentenca = _sentenca(texto)

    classe = _valor_apos(linhas, "Classe da ação", "Classe da Ação", "Classe")
    assunto = ""
    for i, l in enumerate(linhas):
        if re.match(r"Assuntos?$", l, re.I):
            for j in range(i + 1, min(i + 8, len(linhas))):
                cand = linhas[j]
                if re.search(r"[A-Za-zÀ-ú]{4,}", cand) and not re.match(
                        r"(Código|Descrição|Principal|Sim|Não|\d+)$", cand, re.I):
                    assunto = cand
                    break
            break

    valor_causa = _valor_apos(linhas, "Valor da Causa", "Valor da causa")

    d = {
        "numero": nproc.group(0) if nproc else "(não identificado)",
        "classe": classe,
        "assunto": assunto,
        "competencia": _valor_apos(linhas, "Competência"),
        "orgao": _valor_apos(linhas, "Órgão Julgador", "Orgao Julgador"),
        "juiz": _valor_apos(linhas, "Juiz(a)", "Juíza", "Juiz"),
        "autuacao": _valor_apos(linhas, "Data de autuação", "Data de Autuação", "Autuação"),
        "situacao": _valor_apos(linhas, "Situação"),
        "valor_causa": valor_causa or (valores[0] if valores else "R$ 0,00"),
        "reu_preso": _valor_apos(linhas, "Réu Preso", "Reu Preso"),
        "partes": partes,
        "papel_dd": _papel_dd(low, ctx, partes),
        "fatos": _fatos(texto),
        "andamentos": andamentos,
        "ultimo_andamento": andamentos[-1] if andamentos else None,
        "sentenca": sentenca,
        "valores": list(dict.fromkeys(valores))[:8],
        "valor_maximo": valor_maximo,
        "alto_valor": valor_maximo >= 50000,
        "riscos": riscos,
        "criminal": "Criminal" in riscos,
        "fraude": "Fraude" in riscos,
        "tem_texto": bool(plano),
    }
    return d
