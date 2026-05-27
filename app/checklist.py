"""Checklist completo de documentos da Due Diligence (todos os tipos).

Cada item tem um MODO:
  - "auto"   : automação total via navegador controlado (abre e captura o PDF).
               Precisa de 'provider' (a classe que sabe operar o site).
  - "abrir"  : abre a página no NAVEGADOR NORMAL da usuária (sem detecção de
               robô) e copia o documento; ela valida o captcha, baixa e sobe o
               PDF. Precisa só da 'url'.
  - "manual" : sem automação ainda (ou pago / sem site eletrônico) -> só upload.

Para automatizar uma certidão nova e fácil, normalmente basta adicionar um item
com modo="abrir" e a 'url' do site.
"""
from __future__ import annotations

from dataclasses import dataclass

from .models import TipoPessoa


@dataclass
class Item:
    nome: str
    grupo: str
    modo: str = "manual"          # auto | abrir | manual
    aplica_pj: bool = True
    aplica_pf: bool = True
    provider: str | None = None   # nome do provedor (quando modo="auto")
    url: str | None = None        # endereço do site (quando modo="abrir")


_RECEITA_CND = "https://servicos.receitafederal.gov.br/servico/certidoes/"
_RECEITA_CARTAO = "https://servicos.receita.fazenda.gov.br/servicos/cnpjreva/cnpjreva_solicitacao.asp"


ITENS = [
    # Federais / nacionais
    Item("CND Federal (Receita/PGFN)", "Federais", modo="abrir", url=_RECEITA_CND),
    Item("CND Trabalhista (TST)", "Federais", modo="auto", provider="CND Trabalhista (TST)"),
    Item("Certidão de Protestos (CENPROT)", "Federais", modo="auto", provider="Certidão de Protestos (CENPROT)"),
    Item("Cartão CNPJ (Comprovante de Inscrição)", "Federais", modo="abrir", url=_RECEITA_CARTAO, aplica_pf=False),
    # Estaduais — Fazenda
    Item("CND Estadual (Fazenda)", "Estaduais"),
    # Justiça Estadual
    Item("Justiça Estadual — Cível 1º grau", "Justiça Estadual"),
    Item("Justiça Estadual — Cível 2º grau", "Justiça Estadual"),
    Item("Justiça Estadual — Criminal 1º grau", "Justiça Estadual"),
    Item("Justiça Estadual — Criminal 2º grau", "Justiça Estadual"),
    # Justiça Federal
    Item("Justiça Federal — Cível 1º grau", "Justiça Federal"),
    Item("Justiça Federal — Cível 2º grau", "Justiça Federal"),
    Item("Justiça Federal — Criminal 1º grau", "Justiça Federal"),
    Item("Justiça Federal — Criminal 2º grau", "Justiça Federal"),
    # Municipais
    Item("CND Municipal", "Municipais"),
    # Documentos que você fornece
    Item("Contrato Social + última alteração", "Você fornece", aplica_pf=False),
    Item("Identidade dos sócios / representante", "Você fornece", aplica_pf=False),
    Item("RG e CPF do representante", "Você fornece", aplica_pj=False),
]


def itens_para(ctx) -> list[Item]:
    return [
        it for it in ITENS
        if (it.aplica_pj if ctx.tipo == TipoPessoa.PJ else it.aplica_pf)
    ]
