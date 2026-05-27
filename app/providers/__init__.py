"""Carrega automaticamente todos os módulos de provedores.

Basta criar um arquivo .py com uma classe decorada com @registrar dentro de
app/providers/ (em qualquer subpasta) que ele passa a ser usado pelo sistema.
"""
from importlib import import_module
from pathlib import Path
from pkgutil import walk_packages

from .base import BaseProvider, provedores_para, registrar  # noqa: F401


def _carregar_todos():
    raiz = Path(__file__).parent
    for info in walk_packages([str(raiz)], prefix=__name__ + "."):
        curto = info.name.rsplit(".", 1)[-1]
        if curto in {"base", "util"}:
            continue
        try:
            import_module(info.name)
        except Exception as e:  # um provedor quebrado não derruba o sistema
            print(f"[providers] não consegui carregar {info.name}: {e}")


_carregar_todos()
