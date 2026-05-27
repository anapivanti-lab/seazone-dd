"""Gera o PARECER JURÍDICO da Due Diligence no formato usado pelo setor de
Franquias (Seazone): qualificação da Franquia/Operador, análise de Certidões,
Processos, Protestos e Pendências, e Conclusão (sem impedimentos OU com
recomendações). Escrita simples e direta; 100% local e gratuito.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from .leitor import _extrair_texto
from .pep import checar as checar_pep

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
    t = _extrair_texto(caminho).lower()
    if not t.strip():
        return "indeterminado"
    if "positiva com efeito" in t or "positiva com efeitos" in t:
        return "negativa"
    if any(k in t for k in ("nada consta", "não constam", "nao constam", "negativ", "inexist")):
        return "negativa"
    if any(k in t for k in ("positiv", "constam débitos", "constam debitos", "consta o débito", "em aberto")):
        return "positiva"
    return "indeterminado"


# ---------------------------------------------------------------- qualificação
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
    if ec.endswith("(a)"):  # "Solteiro(a)" -> "Solteira" / "Solteiro"
        base = ec[:-3]
        ec = (base[:-1] + "a") if g == "f" else base
    ec = ec.lower() if ec else "estado civil não informado"
    end = ctx.endereco or "endereço não informado"
    return (f"{ctx.nome or 'Nome não informado'}, {bras}, {ec}, {insc} no CPF sob o nº "
            f"{_fmt(ctx.documento, False)}, residente e {domic} em {end}.")


# ---------------------------------------------------------------- análise
def gerar(job) -> dict:
    ctx = job.ctx
    dados = getattr(job, "cnpj_dados", {}) or {}
    pj = ctx.tipo.value == "PJ"
    sujeito = "a Franquia" if pj else ("a Operadora" if _genero(ctx.nome) == "f" else "o Operador")
    de_quem = "da Franquia" if pj else ("da Operadora" if _genero(ctx.nome) == "f" else "do Operador")

    # 1) Certidões coletadas (lê o PDF e classifica negativa/positiva)
    GRUPOS = ("Federais", "Estaduais", "Justiça Estadual", "Justiça Federal", "Municipais")
    certs = [{"nome": p.nome, "classe": _classificar(p.arquivo)}
             for p in job.passos if p.arquivo and p.grupo in GRUPOS and "Protesto" not in p.nome]
    positivas = [c for c in certs if c["classe"] == "positiva"]
    indet = [c for c in certs if c["classe"] == "indeterminado"]

    # 2) Protestos
    passo_prot = next((p for p in job.passos if "Protesto" in p.nome), None)
    prot_classe = _classificar(passo_prot.arquivo) if (passo_prot and passo_prot.arquivo) else "sem"

    # 3) Processos lidos
    procs = job.processos or []
    crim = [pr for pr in procs if pr.get("criminal")]
    fraude = [pr for pr in procs if pr.get("fraude")]
    valores = [pr.get("valor_maximo") or 0 for pr in procs]
    maior_valor = max(valores) if valores else 0.0
    total_proc = sum(valores)

    # 4) PEP
    socios = dados.get("socios", [])
    pep = checar_pep([], cpf=ctx.documento) if not pj else checar_pep(socios)

    # 5) Situação cadastral + pendências (documentos que você fornece e ainda não subiu)
    situacao = dados.get("situacao", "")
    irregular = bool(situacao) and situacao != "ATIVA"
    pendencias = [p.nome for p in job.passos if p.grupo == "Você fornece" and not p.arquivo]

    # ---- textos da análise ----
    if not certs:
        t_cert = "Não há certidões coletadas até o momento."
    elif positivas:
        t_cert = ("Constam certidões POSITIVAS em nome " + de_quem + ": "
                  + "; ".join(c["nome"] for c in positivas) + ".")
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
            num = pr.get("numero") or "s/ número"
            val = pr.get("valor_maximo") or 0
            extra = f", com débito/valor de causa de {_reais(val)}" if val else ""
            riscos = ", ".join(pr.get("riscos") or []) or "a classificar"
            itens.append(f"Processo nº {num} ({riscos}){extra}")
        t_proc = ("Foram localizados os seguintes processos: " + "; ".join(itens) + ". "
                  "Recomenda-se a leitura detalhada de cada um.")

    if prot_classe == "negativa":
        t_prot = f"Não há registros de títulos protestados em nome {de_quem}."
    elif prot_classe == "positiva":
        t_prot = (f"Constam títulos protestados em nome {de_quem} — verifique a quantidade e os "
                  "valores no detalhamento da certidão de protestos.")
    else:
        t_prot = "Certidão de protestos pendente de emissão/verificação."

    t_pend = ("Restam pendentes de envio: " + "; ".join(pendencias) + ".") if pendencias else ""

    # ---- conclusão / risco / recomendações ----
    motivos, recom = [], []
    if positivas:
        motivos.append("certidão(ões) positiva(s)")
        recom.append("Regularizar a situação fiscal, com o pagamento dos débitos e a reversão da(s) "
                     "certidão(ões) positiva(s).")
    if prot_classe == "positiva":
        motivos.append("protestos")
        recom.append("Pagamento/baixa dos títulos protestados.")
    if crim:
        motivos.append("processo(s) criminal(is)")
        recom.append("Análise detalhada do(s) processo(s) criminal(is) antes da contratação.")
    if procs:
        motivos.append("ações judiciais")
        if total_proc:
            recom.append(f"Regularização da situação financeira decorrente das ações judiciais "
                         f"(débito/valor não atualizado de {_reais(total_proc)}).")
    if irregular:
        motivos.append(f"situação cadastral {situacao}")
        recom.append(f"Regularização da situação cadastral ({situacao}) do CNPJ.")
    if pep.get("pep"):
        nomes = "; ".join(f"{p['nome']} ({p['funcao']})" for p in pep["pep"])
        motivos.append("possível pessoa politicamente exposta (PEP)")
        recom.append(f"Verificação quanto à exposição política identificada: {nomes}.")
    if pendencias:
        recom.append("Envio dos documentos pendentes: " + "; ".join(pendencias) + ".")

    if crim or fraude or positivas or irregular:
        risco = "ALTO"
    elif motivos or maior_valor >= 50000 or indet or prot_classe != "negativa":
        risco = "MÉDIO"
    else:
        risco = "BAIXO"

    if not motivos and not pendencias and risco == "BAIXO":
        conclusao = ("Após realizada a análise da documentação elencada acima, certificou-se que, "
                     "estritamente em relação aos documentos apresentados pela franquia e os emitidos "
                     "pelo setor Jurídico da Seazone, estes não apresentam riscos, impedimentos ou "
                     "restrições que possam influenciar na concessão da franquia. Logo, não há "
                     "impedimentos, podendo seguir com a contratação.")
        recomendacoes = []
    else:
        resumo = (", ".join(motivos[:-1]) + " e " + motivos[-1]) if len(motivos) > 1 else (motivos[0] if motivos else "pendências documentais")
        conclusao = (f"A análise identificou os seguintes pontos de atenção: {resumo}. "
                     "Recomenda-se o saneamento das pendências abaixo. Com a conclusão das "
                     "recomendações, é possível seguir com a contratação.")
        recomendacoes = recom

    docs_analisados = [p.nome for p in job.passos if p.arquivo] + [f"Processo: {pr.get('arquivo','')}" for pr in procs]

    d = {
        "tipo": ctx.tipo.value, "nome": ctx.nome, "documento": ctx.documento,
        "risco": risco, "conclusao": conclusao, "recomendacoes": recomendacoes,
        "qual_franquia": _qual_franquia(ctx, dados), "qual_operador": _qual_operador(ctx, dados),
        "secao_principal": "Franquia" if pj else "Operador",
        "certidoes_txt": t_cert, "processos_txt": t_proc, "protestos_txt": t_prot, "pendencias_txt": t_pend,
        "docs_analisados": docs_analisados, "situacao": situacao,
        "cnae": dados.get("cnae_codigo", ""), "cnae_desc": dados.get("cnae_descricao", ""),
        "gerado_em": datetime.now().strftime("%d/%m/%Y %H:%M"), "data_extenso": _data_extenso(),
    }
    corpo = _corpo_html(d)
    pagina = (f'<!doctype html><html lang="pt-br"><head><meta charset="utf-8">'
              f'<title>Parecer Jurídico — {ctx.nome or ctx.documento}</title>'
              f"<style>{_ESTILO}</style></head><body>{corpo}</body></html>")
    d["html"] = pagina
    _salvar_html(job, pagina)
    return d


# ---------------------------------------------------------------- HTML
_CORES = {"ALTO": "#c0392b", "MÉDIO": "#b8860b", "BAIXO": "#1a7d3c"}


def _bloco_analise(d) -> str:
    """Bloco Certidões/Processos/Protestos/Pendências da seção principal."""
    pend = f'<p class="sub">Pendências:</p><p>{d["pendencias_txt"]}</p>' if d["pendencias_txt"] else ""
    return (f'<p class="sub">Certidões:</p><p>{d["certidoes_txt"]}</p>'
            f'<p class="sub">Processos:</p><p>{d["processos_txt"]}</p>'
            f'<p class="sub">Protestos:</p><p>{d["protestos_txt"]}</p>'
            f"{pend}")


def _corpo_html(d) -> str:
    cor = _CORES.get(d["risco"], "#1a7d3c")
    docs = "".join(f"<li>{x}</li>" for x in d["docs_analisados"]) or "<li>(documentos serão listados conforme emitidos/anexados)</li>"
    franquia_bloco = _bloco_analise(d) if d["secao_principal"] == "Franquia" else \
        "<p>Todas as certidões e análises constam na seção do Operador.</p>" if d["tipo"] == "PF" else ""
    operador_bloco = _bloco_analise(d) if d["secao_principal"] == "Operador" else \
        "<p>Documentação do(s) sócio(s)/representante(s) a ser analisada individualmente.</p>"
    recs = ""
    if d["recomendacoes"]:
        itens = "".join(f"<li>{r}</li>" for r in d["recomendacoes"])
        recs = f'<p class="sub">Recomendações:</p><ol class="rec">{itens}</ol>'
    cnae = f' · CNAE: {d["cnae"]} {d["cnae_desc"]}' if d["cnae"] else ""
    sit = f' · Situação cadastral: {d["situacao"]}' if d["situacao"] else ""
    return f"""
    <div class="cab">
      <div class="marca">SEAZONE · DEPARTAMENTO JURÍDICO</div>
      <h1>PARECER JURÍDICO — DUE DILIGENCE<br>{d['nome'] or d['documento']}</h1>
      <span class="badge" style="background:{cor}">Risco: {d['risco']}</span>
    </div>

    <h2>1. Qualificação</h2>
    <p class="q"><b>Franquia:</b> {d['qual_franquia']}</p>
    <p class="q"><b>Operador:</b> {d['qual_operador']}</p>

    <h2>2. Documentos analisados</h2>
    <ul>{docs}</ul>
    <p class="obs2">Dados cadastrais: {d['tipo']}{sit}{cnae}.</p>

    <h2>3. Parecer</h2>
    <p class="ent">Franquia</p>{franquia_bloco}
    <p class="ent">Operador</p>{operador_bloco}

    <h2>4. Conclusão</h2>
    <p>{d['conclusao']}</p>
    {recs}

    <p class="assinatura">{d['data_extenso']}<br><br>
      ____________________________________<br><b>Departamento Jurídico — Seazone</b></p>
    <p class="rodape">Documento gerado automaticamente pelo sistema de Due Diligence em {d['gerado_em']}.
      Revise antes de encaminhar ao setor de Franquias.</p>
    """


_ESTILO = """
body{font-family:Georgia,'Times New Roman',serif;color:#1a2332;max-width:820px;margin:2rem auto;line-height:1.65;padding:0 1.5rem;background:#fff}
.cab{text-align:center;border-bottom:3px solid #0b4f6c;padding-bottom:1rem;margin-bottom:1rem}
.marca{color:#0b4f6c;font-weight:700;letter-spacing:2px;font-size:.78rem}
h1{font-size:1.2rem;margin:.5rem 0 .9rem;font-weight:700}
h2{font-size:1.02rem;color:#0b4f6c;border-bottom:1px solid #d3dde3;padding-bottom:.2rem;margin:1.6rem 0 .5rem}
p{text-align:justify;margin:.35rem 0}
.q b{color:#0b4f6c}
.ent{font-weight:700;margin-top:.8rem;text-decoration:underline}
.sub{font-weight:700;margin:.5rem 0 .1rem}
.badge{display:inline-block;padding:.25rem .9rem;border-radius:999px;color:#fff;font-weight:700;font-size:.82rem}
.obs2{color:#5a6b7a;font-size:.85rem}
ul,ol{margin:.3rem 0 .3rem 1.2rem}.rec li{margin:.25rem 0}
.assinatura{margin-top:2.4rem;text-align:center}
.rodape{margin-top:1.6rem;color:#8a97a3;font-size:.76rem;border-top:1px solid #eee;padding-top:.6rem;text-align:left}
"""


def _salvar_html(job, pagina) -> Path:
    destino = job.ctx.pasta_saida / "Parecer_Juridico_DD.html"
    destino.write_text(pagina, encoding="utf-8")
    return destino
