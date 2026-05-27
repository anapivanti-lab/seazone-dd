"""Servidor web local do sistema de Due Diligence de Franquias (Seazone)."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .checklist import itens_para
from .config import PASTA_PROCESSOS
from .extrator import extrair_cartao_cnpj, extrair_identidade
from .leitor import analisar
from .models import Contexto, TipoPessoa
from .ocr import ler as ler_identidade
from .parecer import gerar as gerar_parecer
from .orchestrator import JOBS, Passo, abrir_item, concluir_job, criar_job, executar_job
from .providers import provedores_para
from .storage import _slug

BASE = Path(__file__).parent
app = FastAPI(title="DD Franquias — Seazone")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE / "templates"))


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    resp = templates.TemplateResponse(request, "index.html")
    resp.headers["Cache-Control"] = "no-store, must-revalidate"  # sempre versão atual
    return resp


@app.get("/provedores")
async def provedores(tipo: str):
    """Certidões com automação (alimenta as caixinhas de 'abrir site')."""
    ctx = Contexto(tipo=TipoPessoa(tipo), documento="0")
    return JSONResponse([p.nome for p in provedores_para(ctx)])


@app.get("/checklist")
async def checklist(tipo: str, uf: str = "", municipio: str = ""):
    """Lista COMPLETA de documentos da DD (reflete o site certo pela UF/cidade)."""
    ctx = Contexto(tipo=TipoPessoa(tipo), documento="0", uf=uf, municipio=municipio)
    return JSONResponse(
        [{"nome": it.nome, "grupo": it.grupo, "modo": it.modo, "obs": it.obs} for it in itens_para(ctx)]
    )


@app.post("/emitir")
async def emitir(
    tipo: str = Form(...),
    documento: str = Form(...),
    nome: str = Form(""),
    uf: str = Form(""),
    municipio: str = Form(""),
    rg: str = Form(""),
    nome_mae: str = Form(""),
    endereco: str = Form(""),
    data_nascimento: str = Form(""),
    selecionados: list[str] = Form(default=[]),
):
    ctx = Contexto(tipo=TipoPessoa(tipo), documento=documento, nome=nome, uf=uf,
                   municipio=municipio, rg=rg, nome_mae=nome_mae, endereco=endereco,
                   data_nascimento=data_nascimento)
    job = criar_job(ctx, selecionados)
    asyncio.create_task(executar_job(job))
    return JSONResponse({"job_id": job.id})


@app.post("/upload/{job_id}")
async def upload(job_id: str, item: str = Form(...), arquivo: UploadFile = File(...)):
    """Sobe manualmente o PDF de um documento e registra na checklist."""
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"erro": "job não encontrado"}, status_code=404)
    conteudo = await arquivo.read()
    ext = Path(arquivo.filename or "").suffix or ".pdf"
    destino = job.ctx.pasta_saida / f"{_slug(item)}{ext}"
    destino.write_bytes(conteudo)
    passo = next((p for p in job.passos if p.nome == item), None)
    if passo is None:
        passo = Passo(nome=item, grupo="Outros documentos", auto=False)
        job.passos.append(passo)
    passo.status = "enviado"
    passo.arquivo = str(destino)
    passo.mensagem = f"Enviado: {arquivo.filename}"
    return JSONResponse(job.to_dict())


@app.post("/ler-processo/{job_id}")
async def ler_processo(job_id: str, arquivo: UploadFile = File(...)):
    """Sobe o PDF de um processo e devolve o resumo (número, partes, valores, riscos)."""
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"erro": "job não encontrado"}, status_code=404)
    conteudo = await arquivo.read()
    base = _slug(Path(arquivo.filename or "processo").stem)
    destino = job.ctx.pasta_saida / f"PROCESSO_{base}.pdf"
    destino.write_bytes(conteudo)
    resumo = analisar(str(destino))
    resumo["arquivo"] = arquivo.filename
    job.processos.append(resumo)
    return JSONResponse(resumo)


@app.post("/parecer/{job_id}")
async def parecer(job_id: str):
    """Gera o parecer de risco (6 critérios) a partir do que foi coletado."""
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"erro": "job não encontrado"}, status_code=404)
    return JSONResponse(gerar_parecer(job))


@app.post("/ler-documento")
async def ler_documento(tipo: str = Form(...), arquivo: UploadFile = File(...)):
    """Lê o documento anexado (PJ = Cartão CNPJ; PF = identidade), imagem ou PDF,
    e devolve os campos que conseguiu extrair (você completa o que faltar)."""
    conteudo = await arquivo.read()
    nome = arquivo.filename or "documento"
    suf = Path(nome).suffix.lower() or (".pdf" if conteudo[:4] == b"%PDF" else ".png")
    tmp = PASTA_PROCESSOS / ("_doc_" + _slug(Path(nome).stem) + suf)
    tmp.write_bytes(conteudo)
    try:
        dados = extrair_cartao_cnpj(str(tmp)) if tipo == "PJ" else extrair_identidade(str(tmp))
    except Exception as e:
        dados = {"ok": False, "erro": f"Falha ao ler o documento: {e}"}
    return JSONResponse(dados)


@app.post("/ler-identidade")
async def ler_identidade_ep(arquivo: UploadFile = File(...)):
    """Lê (OCR) uma imagem de RG/CNH e devolve RG, nome da mãe e nascimento."""
    conteudo = await arquivo.read()
    nome = arquivo.filename or "identidade.png"
    tmp = PASTA_PROCESSOS / ("_id_" + _slug(Path(nome).stem) + (Path(nome).suffix or ".png"))
    tmp.write_bytes(conteudo)
    return JSONResponse(ler_identidade(str(tmp)))


@app.post("/concluir/{job_id}")
async def concluir(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"erro": "job não encontrado"}, status_code=404)
    await concluir_job(job)
    return JSONResponse(job.to_dict())


@app.post("/abrir-pasta/{job_id}")
async def abrir_pasta(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"erro": "job não encontrado"}, status_code=404)
    try:
        os.startfile(job.ctx.pasta_saida)  # abre o Explorer na pasta (Windows)
    except Exception as e:
        return JSONResponse({"erro": str(e)}, status_code=500)
    return JSONResponse({"ok": True})


@app.post("/abrir-item/{job_id}")
async def abrir_item_ep(job_id: str, nome: str = Form(...)):
    """Abre/emite UM item (botão 'Abrir site') — um de cada vez, sem floodar abas."""
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"erro": "job não encontrado"}, status_code=404)
    await abrir_item(job, nome)
    return JSONResponse(job.to_dict())


@app.post("/abrir-arquivo/{job_id}")
async def abrir_arquivo(job_id: str, nome: str = Form(...)):
    """Abre o PDF já capturado de um item específico (no visualizador padrão)."""
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"erro": "job não encontrado"}, status_code=404)
    passo = next((p for p in job.passos if p.nome == nome and p.arquivo), None)
    if not passo:
        return JSONResponse({"erro": "esse item ainda não tem PDF salvo"}, status_code=404)
    try:
        os.startfile(passo.arquivo)
    except Exception as e:
        return JSONResponse({"erro": str(e)}, status_code=500)
    return JSONResponse({"ok": True})


@app.get("/status/{job_id}")
async def status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"erro": "job não encontrado"}, status_code=404)
    return JSONResponse(job.to_dict())
