"""Gera o parecer de risco da Due Diligence: junta certidões, protestos e
processos lidos e preenche os 6 critérios de risco. 100% local e gratuito.

Status de cada critério: "ok" (verde), "alerta" (vermelho) ou "revisar" (o
sistema não consegue decidir sozinho — você confere).
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .leitor import _extrair_texto

CRITERIOS = [
    "1. Todas as certidões são negativas (ou positivas com efeito de negativa)?",
    "2. Inexiste processo criminal envolvendo o representante/franquia?",
    "3. O CNAE utilizado pela franquia está correto?",
    "4. O representante legal não é pessoa politicamente exposta (PEP)?",
    "5. Inexistem protestos em nome da franquia/representante?",
    "6. Inexistem processos cíveis relacionados ao objeto da franquia?",
]


def _classificar(caminho: str) -> str:
    t = _extrair_texto(caminho).lower()
    if not t.strip():
        return "indeterminado"
    if "positiva com efeito" in t or "positiva com efeitos" in t:
        return "negativa"  # equiparada a negativa
    if any(k in t for k in ("nada consta", "não constam", "nao constam", "negativ", "inexist")):
        return "negativa"
    if any(k in t for k in ("positiv", "constam débitos", "constam debitos", "consta o débito", "em aberto")):
        return "positiva"
    return "indeterminado"


def gerar(job) -> dict:
    ctx = job.ctx
    certidoes = []
    for p in job.passos:
        if p.arquivo:
            certidoes.append({"nome": p.nome, "grupo": p.grupo, "classe": _classificar(p.arquivo)})

    positivas = [c for c in certidoes if c["classe"] == "positiva"]
    indet = [c for c in certidoes if c["classe"] == "indeterminado"]
    crim = [pr for pr in job.processos if pr.get("criminal")]
    fraude = [pr for pr in job.processos if pr.get("fraude")]
    civel = [pr for pr in job.processos if "Cível/Cobrança" in (pr.get("riscos") or [])]
    prot = next((c for c in certidoes if "Protesto" in c["nome"]), None)

    crits = []
    # 1 — certidões negativas?
    if not certidoes:
        crits.append(("revisar", "Nenhuma certidão coletada ainda."))
    elif positivas:
        crits.append(("alerta", "Certidão(ões) POSITIVA(s): " + ", ".join(c["nome"] for c in positivas)))
    elif indet:
        crits.append(("revisar", f"{len(indet)} certidão(ões) não lida(s) automaticamente — confira."))
    else:
        crits.append(("ok", "Todas as certidões lidas vieram negativas."))
    # 2 — criminal?
    crits.append(("alerta", f"{len(crim)} processo(s) criminal(is) detectado(s).") if crim
                 else ("ok", "Nenhum processo criminal nos PDFs lidos."))
    # 3 — CNAE
    crits.append(("revisar", "Confirme o CNAE no Cartão CNPJ coletado."))
    # 4 — PEP
    crits.append(("revisar", "Confirme se o representante é PEP (verificação manual)."))
    # 5 — protestos
    if prot and prot["classe"] == "negativa":
        crits.append(("ok", "Certidão de protestos negativa."))
    elif prot and prot["classe"] == "positiva":
        crits.append(("alerta", "Certidão de protestos POSITIVA — há protestos."))
    else:
        crits.append(("revisar", "Verifique a certidão de protestos."))
    # 6 — cíveis
    crits.append(("alerta", f"{len(civel) + len(fraude)} processo(s) cível(is)/fraude detectado(s).")
                 if (civel or fraude) else ("ok", "Nenhum processo cível relevante nos PDFs lidos."))

    if crim or fraude or positivas:
        risco = "ALTO"
    elif any(c[0] == "alerta" for c in crits):
        risco = "MÉDIO"
    else:
        risco = "BAIXO (sem alertas automáticos — revise e conclua)"

    dados = {
        "tipo": ctx.tipo.value, "documento": ctx.documento, "nome": ctx.nome,
        "uf": ctx.uf, "municipio": ctx.municipio, "risco": risco,
        "criterios": [{"texto": CRITERIOS[i], "status": crits[i][0], "obs": crits[i][1]} for i in range(6)],
        "certidoes": certidoes, "processos": job.processos,
        "gerado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }
    _salvar_html(job, dados)
    return dados


_COR = {"ok": ("✅", "#1a7d3c"), "alerta": ("⚠️", "#c0392b"), "revisar": ("🔎", "#b8860b")}


def _salvar_html(job, d: dict) -> Path:
    linhas = ""
    for c in d["criterios"]:
        ic, cor = _COR.get(c["status"], ("•", "#333"))
        linhas += (f'<tr><td style="color:{cor}">{ic} {c["status"].upper()}</td>'
                   f'<td>{c["texto"]}</td><td>{c["obs"]}</td></tr>')
    procs = "".join(
        f"<li>{p.get('arquivo','Processo')} — nº {p.get('numero','')} — riscos: "
        f"{', '.join(p.get('riscos') or []) or 'nenhum'}</li>" for p in d["processos"]
    ) or "<li>(nenhum processo lido)</li>"
    cor_risco = {"ALTO": "#c0392b", "MÉDIO": "#b8860b"}.get(d["risco"].split()[0], "#1a7d3c")
    html = f"""<!doctype html><html lang="pt-br"><head><meta charset="utf-8">
<title>Parecer de Risco — {d['nome'] or d['documento']}</title>
<style>body{{font-family:Segoe UI,Arial,sans-serif;margin:2rem;color:#1a2b3c}}
table{{border-collapse:collapse;width:100%;margin:1rem 0}}td,th{{border:1px solid #ddd;padding:.5rem;font-size:.9rem;text-align:left}}
th{{background:#f5f5f5}}.risco{{font-size:1.3rem;font-weight:700;color:{cor_risco}}}</style></head><body>
<h1>Parecer de Risco — Due Diligence</h1>
<p><b>{d['tipo']}</b> — {d['nome'] or '(sem nome)'} — {d['documento']} — {d['municipio']}/{d['uf']}<br>
Gerado em {d['gerado_em']}</p>
<p>Classificação de risco: <span class="risco">{d['risco']}</span></p>
<h2>Critérios</h2>
<table><tr><th>Status</th><th>Critério</th><th>Observação</th></tr>{linhas}</table>
<h2>Processos lidos</h2><ul>{procs}</ul>
<p style="color:#888;font-size:.8rem">Documento gerado automaticamente — revise antes de concluir.</p>
</body></html>"""
    destino = job.ctx.pasta_saida / "parecer.html"
    destino.write_text(html, encoding="utf-8")
    return destino
