"""Base para os 'provedores' de certidão.

Cada certidão (CND Federal, Trabalhista, Protestos, etc.) é um provedor:
uma pequena classe que sabe navegar em UM site e emitir UMA certidão.
Adicionar uma nova certidão = criar uma nova classe e registrá-la com @registrar.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..config import TIMEOUT_CAPTCHA
from ..models import Contexto, Resultado, Status, TipoPessoa
from .util import salvar_download, salvar_screenshot

if TYPE_CHECKING:
    from playwright.async_api import Page

# Registro global de provedores (preenchido pelo decorador @registrar)
_PROVEDORES: list["BaseProvider"] = []


def registrar(cls):
    """Decorador que registra um provedor para o sistema usar."""
    _PROVEDORES.append(cls())
    return cls


def provedores_para(ctx: Contexto) -> list["BaseProvider"]:
    """Retorna os provedores aplicáveis ao contexto (PJ/PF, UF, município)."""
    return [p for p in _PROVEDORES if p.disponivel_para(ctx)]


class BaseProvider:
    nome: str = "Certidão"
    nivel: str = "federal"        # federal | nacional | estadual | municipal
    aplica_pj: bool = True
    aplica_pf: bool = True
    # UFs onde este provedor faz sentido (vazio = todas). Ex.: ["SC"]
    ufs: list[str] = []

    def disponivel_para(self, ctx: Contexto) -> bool:
        if ctx.tipo == TipoPessoa.PJ and not self.aplica_pj:
            return False
        if ctx.tipo == TipoPessoa.PF and not self.aplica_pf:
            return False
        if self.ufs and ctx.uf and ctx.uf not in self.ufs:
            return False
        return True

    async def emitir(self, ctx: Contexto, page: "Page") -> Resultado:
        raise NotImplementedError

    async def _fluxo_assistido(self, page, ctx, url, nome_arquivo, preencher=None) -> Resultado:
        """Padrão comum: abre o site, preenche o documento e espera o PDF.

        Funciona COM captcha: depois que o sistema preenche os dados, você
        resolve o captcha e clica em consultar/emitir na janela do navegador;
        o sistema captura o PDF baixado automaticamente.
        """
        await page.goto(url, wait_until="domcontentloaded")
        if preencher is not None:
            try:
                await preencher(page, ctx)
            except Exception:
                # Se o seletor do campo mudou, seguimos: você preenche na tela.
                pass
        try:
            async with page.expect_download(timeout=TIMEOUT_CAPTCHA * 1000) as info:
                pass  # aguarda você concluir (captcha + clique) e o download iniciar
            arquivo = await salvar_download(await info.value, ctx, nome_arquivo)
            return self._ok(arquivo)
        except Exception:
            arquivo = await salvar_screenshot(page, ctx, nome_arquivo + "_TELA")
            return self._pendente(
                "Não capturei o PDF sozinho (vamos calibrar este site). Salvei a tela como evidência."
            )

    # ----- atalhos para montar o Resultado -----
    def _ok(self, arquivo=None, msg="") -> Resultado:
        return Resultado(self.nome, Status.SUCESSO, arquivo=arquivo, mensagem=msg)

    def _indisponivel(self, msg: str) -> Resultado:
        return Resultado(self.nome, Status.INDISPONIVEL, mensagem=msg)

    def _pendente(self, msg: str = "Aguardando você resolver o captcha") -> Resultado:
        return Resultado(self.nome, Status.PENDENTE, mensagem=msg)

    def _erro(self, msg: str) -> Resultado:
        return Resultado(self.nome, Status.ERRO, mensagem=msg)
