"""Servidor web local do sistema de Due Diligence de Franquias (Seazone)."""
from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .models import Contexto, TipoPessoa
from .orchestrator import JOBS, criar_job, executar_job

BASE = Path(__file__).parent
app = FastAPI(title="DD Franquias — Seazone")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE / "templates"))


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/emitir")
async def emitir(
    tipo: str = Form(...),
    documento: str = Form(...),
    nome: str = Form(""),
    uf: str = Form(""),
    municipio: str = Form(""),
):
    ctx = Contexto(tipo=TipoPessoa(tipo), documento=documento, nome=nome, uf=uf, municipio=municipio)
    job = criar_job(ctx)
    # roda a emissão em segundo plano; a tela acompanha pelo /status
    asyncio.create_task(executar_job(job))
    return JSONResponse({"job_id": job.id})


@app.get("/status/{job_id}")
async def status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"erro": "job não encontrado"}, status_code=404)
    return JSONResponse(job.to_dict())
