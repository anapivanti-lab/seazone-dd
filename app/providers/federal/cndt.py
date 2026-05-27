"""CNDT — Certidão Negativa de Débitos Trabalhistas (TST). Serve para PJ e PF.
(Confirmado funcionando na calibração.)"""
from ..base import BaseProvider, registrar


@registrar
class CNDTrabalhista(BaseProvider):
    nome = "CND Trabalhista (TST)"
    nome_arquivo = "CND_Trabalhista"
    URL = "https://cndt-certidao.tst.jus.br/inicio.faces"
    SELETOR = "input[id*='cpfCnpj'], input[type='text']"
