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
from .models import Contexto, TipoPessoa
from .orchestrator import JOBS, Passo, concluir_job, criar_job, executar_job
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
async def checklist(tipo: str):
    """Lista COMPLETA de documentos da DD (para mostrar tudo já na abertura)."""
    ctx = Contexto(tipo=TipoPessoa(tipo), documento="0")
    return JSONResponse(
        [{"nome": it.nome, "grupo": it.grupo, "auto": it.provider is not None} for it in itens_para(ctx)]
    )


@app.post("/emitir")
async def emitir(
    tipo: str = Form(...),
    documento: str = Form(...),
    nome: str = Form(""),
    uf: str = Form(""),
    municipio: str = Form(""),
    selecionados: list[str] = Form(default=[]),
):
    ctx = Contexto(tipo=TipoPessoa(tipo), documento=documento, nome=nome, uf=uf, municipio=municipio)
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


@app.get("/status/{job_id}")
async def status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"erro": "job não encontrado"}, status_code=404)
    return JSONResponse(job.to_dict())
