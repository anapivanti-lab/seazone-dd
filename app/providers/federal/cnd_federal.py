"""CND Federal — Certidão de Débitos Relativos a Créditos Tributários Federais
e à Dívida Ativa da União (Receita Federal + PGFN). Serve para PJ e PF.

A página oficial atual é um aplicativo único que aceita CPF ou CNPJ.
"""
from ..base import BaseProvider, registrar


@registrar
class CNDFederal(BaseProvider):
    nome = "CND Federal (Receita/PGFN)"
    nome_arquivo = "CND_Federal"
    URL = "https://servicos.receitafederal.gov.br/servico/certidoes/"
    SELETOR = "input[type='text'], input"
