"""Base para os 'provedores' de certidão.

Cada certidão é um provedor: uma classe pequena que sabe abrir UM site e
preencher o documento. Na maioria dos casos basta declarar a URL e o seletor
do campo; o resto é herdado daqui.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..models import Contexto, TipoPessoa

if TYPE_CHECKING:
    from playwright.async_api import Page

# Registro global de provedores (preenchido pelo decorador @registrar)
_PROVEDORES: list["BaseProvider"] = []


def registrar(cls):
    """Decorador que registra um provedor para o sistema usar."""
    _PROVEDORES.append(cls())
    return cls


def provedores_para(ctx: Contexto) -> list["BaseProvider"]:
    """Retorna os provedores aplicáveis ao contexto (PJ/PF, UF)."""
    return [p for p in _PROVEDORES if p.disponivel_para(ctx)]


def provedor_por_nome(nome: str):
    """Acha um provedor registrado pelo seu nome (ou None)."""
    for p in _PROVEDORES:
        if p.nome == nome:
            return p
    return None


class BaseProvider:
    nome: str = "Certidão"
    nivel: str = "federal"        # federal | nacional | estadual | municipal
    aplica_pj: bool = True
    aplica_pf: bool = True
    ufs: list[str] = []           # vazio = todas as UFs; ex.: ["SC"]
    nome_arquivo: str = "Certidao"  # base do nome do PDF salvo
    URL: str = ""                 # endereço fixo do site
    SELETOR: str = "input[type='text']"  # onde digitar o CNPJ/CPF
    auto_completo: bool = False   # True = 100% automático, headless (sites sem captcha/login)

    def disponivel_para(self, ctx: Contexto) -> bool:
        if ctx.tipo == TipoPessoa.PJ and not self.aplica_pj:
            return False
        if ctx.tipo == TipoPessoa.PF and not self.aplica_pf:
            return False
        if self.ufs and ctx.uf and ctx.uf not in self.ufs:
            return False
        return True

    def url(self, ctx: Contexto) -> str:
        """Endereço a abrir. Sobrescreva quando depender de PJ/PF, UF, etc."""
        return self.URL

    async def abrir(self, ctx: Contexto, page: "Page") -> None:
        """Abre o site e preenche o documento.

        NÃO espera o download: quem conclui (captcha + clique em emitir) é você,
        no seu tempo. Qualquer PDF que o site baixar é capturado pelo sistema.
        """
        await page.goto(self.url(ctx), wait_until="domcontentloaded", timeout=60000)
        if self.SELETOR:
            try:
                await page.locator(self.SELETOR).first.fill(ctx.documento, timeout=8000)
            except Exception:
                pass  # se o campo mudou de lugar, você preenche na tela

    async def executar(self, ctx: Contexto, page: "Page"):
        """Fluxo 100% automático (headless): preenche, emite e devolve o caminho
        do PDF. Usado apenas quando auto_completo=True."""
        raise NotImplementedError
