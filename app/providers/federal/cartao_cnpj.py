"""Cartão CNPJ — Comprovante de Inscrição e Situação Cadastral (Receita Federal).
Apenas PJ. Também é a fonte do CNAE (usado no critério de risco nº 3)."""
from ..base import BaseProvider, registrar


@registrar
class CartaoCNPJ(BaseProvider):
    nome = "Cartão CNPJ (Comprovante de Inscrição)"
    nome_arquivo = "Cartao_CNPJ"
    aplica_pf = False
    URL = "https://servicos.receita.fazenda.gov.br/servicos/cnpjreva/cnpjreva_solicitacao.asp"
    SELETOR = "input[name*='cnpj'], input[type='text']"
