"""Funções utilitárias compartilhadas pelos provedores de certidão."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path


def caminho_saida(ctx, nome_base: str, ext: str) -> Path:
    """Monta o caminho do arquivo dentro da pasta da DD, com prefixo do papel e data."""
    from ..storage import com_prefixo
    carimbo = datetime.now().strftime("%Y%m%d")
    nome = com_prefixo(ctx, f"{nome_base}_{carimbo}.{ext.lstrip('.')}")
    destino = ctx.pasta_saida / nome
    destino.parent.mkdir(parents=True, exist_ok=True)
    return destino


async def salvar_download(download, ctx, nome_base: str) -> Path:
    """Salva um download disparado pelo site (geralmente o PDF da certidão)."""
    sufixo = Path(download.suggested_filename).suffix or ".pdf"
    destino = caminho_saida(ctx, nome_base, sufixo)
    await download.save_as(str(destino))
    # Alguns sites baixam o PDF sem extensão / com extensão errada — se o
    # conteúdo for PDF, garante que o arquivo termine em .pdf (pra abrir normal).
    try:
        with open(destino, "rb") as f:
            cabecalho = f.read(5)
        if cabecalho.startswith(b"%PDF") and destino.suffix.lower() != ".pdf":
            novo = destino.with_suffix(".pdf")
            destino.replace(novo)
            destino = novo
    except Exception:
        pass
    return destino


async def salvar_screenshot(page, ctx, nome_base: str) -> Path:
    """Salva uma imagem da tela atual (usado como evidência/fallback)."""
    destino = caminho_saida(ctx, nome_base, "png")
    await page.screenshot(path=str(destino), full_page=True)
    return destino
