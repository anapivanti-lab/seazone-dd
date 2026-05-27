"""Funções utilitárias compartilhadas pelos provedores de certidão."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path


def caminho_saida(ctx, nome_base: str, ext: str) -> Path:
    """Monta o caminho do arquivo dentro da pasta da franquia, com data."""
    carimbo = datetime.now().strftime("%Y%m%d")
    nome = f"{nome_base}_{carimbo}.{ext.lstrip('.')}"
    destino = ctx.pasta_saida / nome
    destino.parent.mkdir(parents=True, exist_ok=True)
    return destino


async def salvar_download(download, ctx, nome_base: str) -> Path:
    """Salva um download disparado pelo site (geralmente o PDF da certidão)."""
    sufixo = Path(download.suggested_filename).suffix or ".pdf"
    destino = caminho_saida(ctx, nome_base, sufixo)
    await download.save_as(str(destino))
    return destino


async def salvar_screenshot(page, ctx, nome_base: str) -> Path:
    """Salva uma imagem da tela atual (usado como evidência/fallback)."""
    destino = caminho_saida(ctx, nome_base, "png")
    await page.screenshot(path=str(destino), full_page=True)
    return destino
