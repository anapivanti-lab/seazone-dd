"""Gera LINKS CLICÁVEIS do Google Drive para os arquivos da DD, sem precisar de
API/OAuth: lê o banco local do Google Drive para Desktop (metadata_sqlite_db),
que mapeia cada arquivo sincronizado ao seu ID no Drive.

Observação: só funciona para arquivos já SINCRONIZADOS (o ID só existe após o
upload). Arquivos recém-criados podem ainda não ter link — aí cai no texto.
"""
from __future__ import annotations

import glob
import os
import shutil
import sqlite3
import tempfile

_DRIVEFS = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "DriveFS")


def _dbs():
    return glob.glob(os.path.join(_DRIVEFS, "*", "metadata_sqlite_db"))


def _abrir_copia(db_path: str):
    """Copia o banco (e o WAL) para um temporário e abre só-leitura (o original
    fica travado pelo Drive)."""
    tmp = tempfile.mkdtemp()
    base = os.path.join(tmp, "m")
    for ext in ("", "-wal", "-shm"):
        try:
            shutil.copy2(db_path + ext, base + ext)
        except Exception:
            pass
    return sqlite3.connect(base)


def urls_da_pasta(pasta_nome: str, nomes_arquivos):
    """Devolve ({nome_arquivo: url_drive}, url_da_pasta). Vazio quando não achar
    (ex.: ainda não sincronizado)."""
    resultado = {n: "" for n in nomes_arquivos}
    url_pasta = ""
    if not pasta_nome:
        return resultado, url_pasta
    for db in _dbs():
        try:
            con = _abrir_copia(db)
            cur = con.cursor()
            fr = cur.execute(
                "select stable_id, id from items where local_title=? and is_folder=1 and trashed=0 limit 1",
                (pasta_nome,)).fetchone()
            if not fr:
                con.close()
                continue
            pasta_sid, pasta_id = fr
            url_pasta = f"https://drive.google.com/drive/folders/{pasta_id}"
            rows = cur.execute(
                "select i.local_title, i.id from items i "
                "join stable_parents sp on sp.item_stable_id=i.stable_id "
                "where sp.parent_stable_id=? and i.trashed=0", (pasta_sid,)).fetchall()
            mapa = {lt: idd for lt, idd in rows}
            for n in nomes_arquivos:
                if mapa.get(n):
                    resultado[n] = f"https://drive.google.com/file/d/{mapa[n]}/view"
            con.close()
            return resultado, url_pasta
        except Exception:
            pass
    return resultado, url_pasta
