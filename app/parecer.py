"""Gera o PARECER JURÍDICO da Due Diligence no formato do setor de Franquias
(Seazone). Produz um documento WORD editável (.docx) e uma prévia em HTML.

Conclusão em 4 níveis:
  1) Nada encontrado  -> texto padrão "não há impedimentos, podendo seguir".
  2) Achado leve (ex.: CND positiva com débito < R$ 10.000) -> texto padrão +
     "Porém, recomendamos: ...".
  3) Risco financeiro real (débitos altos, execuções, protestos) -> bloco
     "Financeiro: ... / Recomendação: 1, 2, 3 / podemos seguir".
  4) Risco irreversível (processo criminal) -> "Processual: ... / Recomendação:
     Não aprovar a concessão da franquia."
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from .extrator import _texto_documento
from .pep import checar as checar_pep

LIMITE_DEBITO = 10000.0  # abaixo disso = achado leve; acima = risco real

TEXTO_OK = ("Após realizada a análise da documentação elencada acima, certificou-se que, "
            "estritamente em relação aos documentos apresentados pela franquia e os emitidos pelo "
            "setor Jurídico da Seazone, estes não apresentam riscos, impedimentos ou restrições que "
            "possam influenciar na concessão da franquia. Logo, não há impedimentos, podendo seguir "
            "com a contratação.")

_MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
          "agosto", "setembro", "outubro", "novembro", "dezembro"]


# ---------------------------------------------------------------- utilidades
def _fmt(doc: str, pj: bool) -> str:
    d = re.sub(r"\D", "", doc or "")
    if pj and len(d) == 14:
        return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"
    if not pj and len(d) == 11:
        return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
    return doc or "—"


def _reais(v: float) -> str:
    return ("R$ " + f"{v:,.2f}").replace(",", "X").replace(".", ",").replace("X", ".")


def _genero(nome: str) -> str:
    p = (nome or "").strip().split()
    return "f" if p and p[0].lower().endswith("a") else "m"


def _data_extenso() -> str:
    d = datetime.now()
    return f"Florianópolis/SC, {d.day} de {_MESES[d.month - 1]} de {d.year}."


def _classificar(caminho: str) -> str:
    t = _texto_documento(caminho).lower()  # lê PDF e também imagem (via OCR)
    if not t.strip():
        return "indeterminado"
    # Comunicado da Receita Federal: quando a CND é POSITIVA não sai a certidão —
    # sai o aviso "informações insuficientes para emitir a certidão". Isso = positiva
    # (há pendência); a franquia precisa regularizar e esclarecer.
    if any(k in t for k in ("insuficientes para emitir", "não foi possível emitir",
                            "nao foi possivel emitir", "não é possível emitir",
                            "nao e possivel emitir", "insuficientes para emitir a certidão")):
        return "positiva"
    if "positiva com efeito" in t or "positiva com efeitos" in t:
        return "negativa"
    if any(k in t for k in ("nada consta", "não constam", "nao constam", "negativ", "inexist")):
        return "negativa"
    if any(k in t for k in ("positiv", "constam débitos", "constam debitos", "consta o débito", "em aberto")):
        return "positiva"
    return "indeterminado"


def _valor_protestos(caminho: str) -> float:
    vals = []
    for m in re.findall(r"R\$\s*([\d.]+,\d{2})", _texto_documento(caminho)):
        try:
            vals.append(float(m.replace(".", "").replace(",", ".")))
        except Exception:
            pass
    return sum(vals)


def _qual_franquia(ctx, dados) -> str:
    if ctx.tipo.value != "PJ":
        return "Não constituído."
    sede = ctx.endereco or dados.get("endereco") or "endereço não informado"
    return (f"{ctx.nome or 'Razão social não informada'}, pessoa jurídica de direito privado, "
            f"inscrita no CNPJ sob o nº {_fmt(ctx.documento, True)}, com sede em {sede}.")


def _qual_operador(ctx, dados) -> str:
    if ctx.tipo.value != "PF":
        socios = dados.get("socios") or []
        if socios:
            return ("Sócio(s)/representante(s): " + ", ".join(socios)
                    + " — documentação individual a ser analisada em DD própria.")
        return "A ser analisado com a documentação do representante legal."
    g = _genero(ctx.nome)
    bras = "brasileira" if g == "f" else "brasileiro"
    insc = "inscrita" if g == "f" else "inscrito"
    domic = "domiciliada" if g == "f" else "domiciliado"
    ec = (ctx.estado_civil or "").strip()
    if ec.endswith("(a)"):
        base = ec[:-3]
        ec = (base[:-1] + "a") if g == "f" else base
    ec = ec.lower() if ec else "estado civil não informado"
    end = ctx.endereco or "endereço não informado"
    return (f"{ctx.nome or 'Nome não informado'}, {bras}, {ec}, {insc} no CPF sob o nº "
            f"{_fmt(ctx.documento, False)}, residente e {domic} em {end}.")


# ---------------------------------------------------------------- núcleo
def gerar(job) -> dict:
    ctx = job.ctx
    dados = getattr(job, "cnpj_dados", {}) or {}
    pj = ctx.tipo.value == "PJ"
    sujeito = "a Franquia" if pj else ("a Operadora" if _genero(ctx.nome) == "f" else "o Operador")
    de_quem = "da Franquia" if pj else ("da Operadora" if _genero(ctx.nome) == "f" else "do Operador")

    GRUPOS = ("Federais", "Estaduais", "Justiça Estadual", "Justiça Federal", "Municipais")
    certs = [{"nome": p.nome, "classe": _classificar(p.arquivo)}
             for p in job.passos if p.arquivo and p.grupo in GRUPOS and "Protesto" not in p.nome]
    positivas = [c for c in certs if c["classe"] == "positiva"]
    indet = [c for c in certs if c["classe"] == "indeterminado"]

    passo_prot = next((p for p in job.passos if "Protesto" in p.nome), None)
    prot_classe = _classificar(passo_prot.arquivo) if (passo_prot and passo_prot.arquivo) else "sem"
    prot_positiva = prot_classe == "positiva"
    total_prot = _valor_protestos(passo_prot.arquivo) if (prot_positiva and passo_prot.arquivo) else 0.0

    procs = job.processos or []
    crim = [pr for pr in procs if pr.get("criminal")]
    total_proc = sum(pr.get("valor_maximo") or 0 for pr in procs)

    socios = dados.get("socios", [])
    situacao = dados.get("situacao", "")
    irregular = bool(situacao) and situacao != "ATIVA"
    pendencias = [p.nome for p in job.passos if p.grupo == "Você fornece" and not p.arquivo]

    # ---- textos da análise ----
    if not certs:
        t_cert = "Não há certidões coletadas até o momento."
    elif positivas:
        t_cert = "Constam certidões POSITIVAS em nome " + de_quem + ": " + "; ".join(c["nome"] for c in positivas) + "."
    elif indet:
        t_cert = ("As certidões foram coletadas. Confira manualmente as que não puderam ser lidas "
                  "automaticamente: " + "; ".join(c["nome"] for c in indet) + ".")
    else:
        t_cert = "Todas as certidões estão regulares (negativas ou positivas com efeito de negativa)."

    if not procs:
        t_proc = (f"Não foram localizados registros de ações judiciais ativas em que {sujeito} "
                  "figure como parte no polo passivo.")
    else:
        itens = []
        for pr in procs:
            cab = f"Processo nº {pr.get('numero') or 's/ número'} — {pr.get('classe') or 'Processo'}"
            if pr.get("assunto"):
                cab += f" (objeto: {pr['assunto']})"
            det = []
            if pr.get("papel_dd"):
                det.append(pr["papel_dd"].rstrip("."))
            if pr.get("valor_maximo"):
                det.append(f"valor/débito de {_reais(pr['valor_maximo'])}")
            if pr.get("situacao"):
                det.append(f"situação atual: {pr['situacao']}")
            if pr.get("sentenca"):
                det.append(f"sentença: {pr['sentenca'].get('resultado')}")
            itens.append(cab + (". " + "; ".join(det) + "." if det else "."))
        t_proc = "Foram localizados os seguintes processos: " + " ".join(itens)

    if prot_classe == "negativa":
        t_prot = f"Não há registros de títulos protestados em nome {de_quem}."
    elif prot_positiva:
        v = f", que totalizam {_reais(total_prot)}" if total_prot else ""
        t_prot = f"Constam títulos protestados em nome {de_quem}{v}."
    else:
        t_prot = "Certidão de protestos pendente de emissão/verificação."

    t_pend = ("Restam pendentes de envio: " + "; ".join(pendencias) + ".") if pendencias else ""

    # ---- conclusão em 4 níveis ----
    debito = total_proc + total_prot

    def recs(grave: bool):
        out = []
        if positivas:
            out.append("Regularizar a situação fiscal junto à Receita Federal e esclarecer/reverter a(s) "
                       "certidão(ões) positiva(s) (quando a CND federal é positiva, a Receita não emite a "
                       "certidão e exibe aviso de informações insuficientes)" if grave
                       else "a regularização e o esclarecimento da(s) certidão(ões) positiva(s)")
        if procs:
            v = f" (débito/valor não atualizado de {_reais(total_proc)})" if total_proc else ""
            out.append(f"Regularização da situação financeira decorrente das ações judiciais{v}" if grave
                       else f"a regularização das ações judiciais encontradas{v}")
        if prot_positiva:
            v = f" ({_reais(total_prot)})" if total_prot else ""
            out.append(f"Pagamento dos protestos{v}" if grave else f"o pagamento/baixa dos protestos{v}")
        if irregular:
            out.append(f"Regularização da situação cadastral ({situacao}) do CNPJ")
        if pendencias:
            out.append("Envio dos documentos pendentes: " + "; ".join(pendencias))
        return out

    risco = "BAIXO"
    categoria = ""        # "" (parágrafo) | "Financeiro" | "Processual"
    concl_texto = TEXTO_OK
    recomendacoes: list[str] = []
    fecho = ""

    achados = bool(positivas or prot_positiva or procs or irregular or pendencias)
    grave = (debito >= LIMITE_DEBITO) or (len(positivas) >= 2) or (prot_positiva and bool(positivas)) \
        or (total_proc >= LIMITE_DEBITO) or (total_prot >= LIMITE_DEBITO)

    if crim:
        risco, categoria = "ALTO", "Processual"
        concl_texto = ("A identificação de processo(s) criminal(is) representa fator de atenção no contexto "
                       "da análise de risco, apresentando riscos relevantes, principalmente reputacionais.")
        recomendacoes = ["Não aprovar a concessão da franquia."]
    elif grave:
        risco, categoria = "ALTO", "Financeiro"
        tipos = []
        if prot_positiva:
            tipos.append("protestos")
        if positivas:
            tipos.append("certidões positivas")
        if procs:
            tipos.append("execuções")
        if irregular:
            tipos.append("situação cadastral irregular")
        resumo = (", ".join(tipos[:-1]) + " e " + tipos[-1]) if len(tipos) > 1 else (tipos[0] if tipos else "os achados")
        concl_texto = resumo[0].upper() + resumo[1:] + " indicam fragilidade de liquidez e histórico de inadimplência relevante."
        recomendacoes = [r if r.endswith(".") else r + "." for r in recs(grave=True)]
        fecho = "Com a conclusão das recomendações acima, podemos seguir com a contratação."
    elif achados:
        risco = "MÉDIO"
        leves = recs(grave=False)
        concl_texto = TEXTO_OK + " Porém, recomendamos: " + "; ".join(leves) + "."
    # else: nível 1 -> TEXTO_OK puro (já é o default)

    docs = [p.nome for p in job.passos if p.arquivo] + [f"Processo: {pr.get('arquivo', '')}" for pr in procs]

    d = {
        "tipo": ctx.tipo.value, "nome": ctx.nome, "documento": ctx.documento,
        "risco": risco, "secao_principal": "Franquia" if pj else "Operador",
        "rotulo_pf": (ctx.papel if (not pj and ctx.papel) else "Operador"),
        "qual_franquia": _qual_franquia(ctx, dados), "qual_operador": _qual_operador(ctx, dados),
        "certidoes_txt": t_cert, "processos_txt": t_proc, "protestos_txt": t_prot, "pendencias_txt": t_pend,
        "concl_categoria": categoria, "concl_texto": concl_texto, "recomendacoes": recomendacoes, "concl_fecho": fecho,
        "docs_analisados": docs, "situacao": situacao,
        "cnae": dados.get("cnae_codigo", ""), "cnae_desc": dados.get("cnae_descricao", ""),
        "gerado_em": datetime.now().strftime("%d/%m/%Y %H:%M"), "data_extenso": _data_extenso(),
    }
    d["html"] = _pagina_html(d)
    d["arquivo"] = str(_salvar_docx(job, d))
    return d


# ---------------------------------------------------------------- blocos comuns
def _analise_pares(d):
    """[(label, texto)] da seção principal (Certidões/Processos/Protestos/Pendências)."""
    pares = [("Certidões:", d["certidoes_txt"]), ("Processos:", d["processos_txt"]),
             ("Protestos:", d["protestos_txt"])]
    if d["pendencias_txt"]:
        pares.append(("Pendências:", d["pendencias_txt"]))
    return pares


# ---------------------------------------------------------------- WORD (.docx)
def _salvar_docx(job, d) -> Path:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt, RGBColor

    AZUL = RGBColor(0x0B, 0x4F, 0x6C)
    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)

    marca = doc.add_paragraph()
    marca.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rm = marca.add_run("SEAZONE · DEPARTAMENTO JURÍDICO")
    rm.bold = True
    rm.font.size = Pt(9)
    rm.font.color.rgb = AZUL

    tit = doc.add_paragraph()
    tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rt = tit.add_run(f"PARECER JURÍDICO — DUE DILIGENCE\n{d['nome'] or d['documento']}")
    rt.bold = True
    rt.font.size = Pt(14)

    def secao(txt):
        p = doc.add_paragraph()
        p.space_before = Pt(10)
        r = p.add_run(txt)
        r.bold = True
        r.font.size = Pt(12)
        r.font.color.rgb = AZUL
        return p

    def label(lbl, texto, recuo=False):
        p = doc.add_paragraph()
        if recuo:
            p.paragraph_format.left_indent = Pt(14)
        r = p.add_run(lbl + " ")
        r.bold = True
        p.add_run(texto)
        return p

    label("Franquia:", d["qual_franquia"])
    label(d["rotulo_pf"] + ":", d["qual_operador"])

    secao("DOCUMENTOS ANALISADOS")
    for x in (d["docs_analisados"] or ["(documentos conforme emitidos/anexados)"]):
        doc.add_paragraph(x, style="List Bullet")

    secao("PARECER")
    label("Franquia", "" if d["secao_principal"] == "Franquia" else
          ("Todas as análises constam na seção do Operador." if d["tipo"] == "PF" else ""))
    if d["secao_principal"] == "Franquia":
        for lbl, txt in _analise_pares(d):
            label(lbl, txt, recuo=True)
    label(d["rotulo_pf"], "" if d["secao_principal"] == "Operador" else
          "Documentação do(s) sócio(s)/representante(s) a ser analisada individualmente.")
    if d["secao_principal"] == "Operador":
        for lbl, txt in _analise_pares(d):
            label(lbl, txt, recuo=True)

    secao("CONCLUSÃO")
    if d["concl_categoria"]:
        label(d["concl_categoria"] + ":", d["concl_texto"])
        rp = doc.add_paragraph()
        rp.add_run("Recomendação:").bold = True
        for r in d["recomendacoes"]:
            doc.add_paragraph(r, style="List Number")
        if d["concl_fecho"]:
            doc.add_paragraph(d["concl_fecho"])
    else:
        doc.add_paragraph(d["concl_texto"])

    doc.add_paragraph()
    ass = doc.add_paragraph()
    ass.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ass.add_run(f"{d['data_extenso']}\n\n____________________________________\n").italic = False
    ass.add_run("Departamento Jurídico — Seazone").bold = True

    rod = doc.add_paragraph()
    rr = rod.add_run(f"Documento gerado automaticamente pelo sistema de Due Diligence em {d['gerado_em']}. "
                     "Revise e ajuste antes de encaminhar ao setor de Franquias.")
    rr.font.size = Pt(8)
    rr.font.color.rgb = RGBColor(0x8A, 0x97, 0xA3)

    from .storage import com_prefixo
    destino = job.ctx.pasta_saida / (com_prefixo(job.ctx, "Parecer_Juridico_DD") + ".docx")
    doc.save(str(destino))
    return destino


# ---------------------------------------------------------------- HTML (prévia)
_CORES = {"ALTO": "#c0392b", "MÉDIO": "#b8860b", "BAIXO": "#1a7d3c"}
_ESTILO = """
body{font-family:Georgia,'Times New Roman',serif;color:#1a2332;max-width:820px;margin:1rem auto;line-height:1.65;padding:0 1.4rem;background:#fff}
.cab{text-align:center;border-bottom:3px solid #0b4f6c;padding-bottom:.8rem;margin-bottom:1rem}
.marca{color:#0b4f6c;font-weight:700;letter-spacing:2px;font-size:.78rem}
h1{font-size:1.18rem;margin:.5rem 0 .8rem;font-weight:700}
h2{font-size:1.0rem;color:#0b4f6c;border-bottom:1px solid #d3dde3;padding-bottom:.2rem;margin:1.4rem 0 .5rem}
p{text-align:justify;margin:.35rem 0}.q b{color:#0b4f6c}
.ent{font-weight:700;margin-top:.7rem;text-decoration:underline}
.sub{font-weight:700;margin:.45rem 0 .1rem;padding-left:.6rem}
.badge{display:inline-block;padding:.2rem .9rem;border-radius:999px;color:#fff;font-weight:700;font-size:.8rem}
.obs2{color:#5a6b7a;font-size:.84rem}ul,ol{margin:.3rem 0 .3rem 1.2rem}.rec li{margin:.25rem 0}
.assinatura{margin-top:2rem;text-align:center}.rodape{margin-top:1.4rem;color:#8a97a3;font-size:.74rem;border-top:1px solid #eee;padding-top:.5rem}
"""


def _corpo_html(d) -> str:
    cor = _CORES.get(d["risco"], "#1a7d3c")
    docs = "".join(f"<li>{x}</li>" for x in d["docs_analisados"]) or "<li>(documentos conforme emitidos/anexados)</li>"
    def bloco(principal):
        if principal:
            return "".join(f'<p class="sub">{l}</p><p>{t}</p>' for l, t in _analise_pares(d))
        if d["tipo"] == "PF":
            return "<p>Todas as análises constam na seção do Operador.</p>"
        return "<p>Documentação do(s) sócio(s)/representante(s) a ser analisada individualmente.</p>"
    franquia = bloco(d["secao_principal"] == "Franquia")
    operador = bloco(d["secao_principal"] == "Operador")
    if d["concl_categoria"]:
        recs = "".join(f"<li>{r}</li>" for r in d["recomendacoes"])
        fecho = f"<p>{d['concl_fecho']}</p>" if d["concl_fecho"] else ""
        concl = (f'<p><b>{d["concl_categoria"]}:</b> {d["concl_texto"]}</p>'
                 f'<p class="sub" style="padding-left:0">Recomendação:</p><ol class="rec">{recs}</ol>{fecho}')
    else:
        concl = f"<p>{d['concl_texto']}</p>"
    cnae = f' · CNAE: {d["cnae"]} {d["cnae_desc"]}' if d["cnae"] else ""
    sit = f' · Situação cadastral: {d["situacao"]}' if d["situacao"] else ""
    return f"""
    <div class="cab"><div class="marca">SEAZONE · DEPARTAMENTO JURÍDICO</div>
      <h1>PARECER JURÍDICO — DUE DILIGENCE<br>{d['nome'] or d['documento']}</h1>
      <span class="badge" style="background:{cor}">Risco: {d['risco']}</span></div>
    <h2>1. Qualificação</h2>
    <p class="q"><b>Franquia:</b> {d['qual_franquia']}</p>
    <p class="q"><b>{d['rotulo_pf']}:</b> {d['qual_operador']}</p>
    <h2>2. Documentos analisados</h2><ul>{docs}</ul>
    <p class="obs2">Dados cadastrais: {d['tipo']}{sit}{cnae}.</p>
    <h2>3. Parecer</h2>
    <p class="ent">Franquia</p>{franquia}
    <p class="ent">{d['rotulo_pf']}</p>{operador}
    <h2>4. Conclusão</h2>{concl}
    <p class="assinatura">{d['data_extenso']}<br><br>____________________________________<br><b>Departamento Jurídico — Seazone</b></p>
    <p class="rodape">Documento gerado automaticamente em {d['gerado_em']}. O arquivo editável está salvo como
      <b>Parecer_Juridico_DD.docx</b> na pasta da franquia.</p>
    """


def _pagina_html(d) -> str:
    return (f'<!doctype html><html lang="pt-br"><head><meta charset="utf-8">'
            f'<title>Parecer Jurídico — {d["nome"] or d["documento"]}</title>'
            f"<style>{_ESTILO}</style></head><body>{_corpo_html(d)}</body></html>")
