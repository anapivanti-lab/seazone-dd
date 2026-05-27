"""CNDT — Certidão Negativa de Débitos Trabalhistas (TST). Serve para PJ e PF.
(Confirmado funcionando na calibração.)"""
from ..base import BaseProvider, registrar


@registrar
class CNDTrabalhista(BaseProvider):
    nome = "CND Trabalhista (TST)"
    nome_arquivo = "CND_Trabalhista"
    URL = "https://cndt-certidao.tst.jus.br/inicio.faces"
    # O campo do CNPJ está na página seguinte (após clicar em "Emitir Certidão").
    # Por ora só abrimos a página inicial; o preenchimento será calibrado depois.
    SELETOR = ""
