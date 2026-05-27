"""Checklist completo de documentos da Due Diligence (todos os tipos).

Itens com 'provider' têm automação (o sistema abre o site). Os demais são
"manuais": você obtém o documento e sobe o PDF pelo próprio sistema.
Conforme formos automatizando mais sites, é só preencher o campo 'provider'.
"""
from __future__ import annotations

from dataclasses import dataclass

from .models import TipoPessoa


@dataclass
class Item:
    nome: str
    grupo: str
    aplica_pj: bool = True
    aplica_pf: bool = True
    provider: str | None = None  # nome do provedor automático, se houver


ITENS = [
    # Federais / nacionais (com automação)
    Item("CND Federal (Receita/PGFN)", "Federais", provider="CND Federal (Receita/PGFN)"),
    Item("CND Trabalhista (TST)", "Federais", provider="CND Trabalhista (TST)"),
    Item("Certidão de Protestos (CENPROT)", "Federais", provider="Certidão de Protestos (CENPROT)"),
    Item("Cartão CNPJ (Comprovante de Inscrição)", "Federais", aplica_pf=False,
         provider="Cartão CNPJ (Comprovante de Inscrição)"),
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
    """Filtra os itens da checklist conforme o tipo (PJ/PF)."""
    return [
        it
        for it in ITENS
        if (it.aplica_pj if ctx.tipo == TipoPessoa.PJ else it.aplica_pf)
    ]
