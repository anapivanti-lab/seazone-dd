"""Certidão de Protestos — CENPROT (consulta nacional de protestos). PJ e PF.
Obs.: a consulta nacional pode exigir cadastro/login gratuito no portal — o
perfil do navegador é persistente, então você só faz o login uma vez."""
from ..base import BaseProvider, registrar


@registrar
class Protestos(BaseProvider):
    nome = "Certidão de Protestos (CENPROT)"
    nome_arquivo = "Protestos_CENPROT"
    nivel = "nacional"
    # Consulta nacional GRATUITA e SEM cadastro (o login só é exigido para
    # emitir a certidão detalhada). Vamos direto na página de consulta.
    URL = "https://www.pesquisaprotesto.com.br/servico/consulta-documento"
    SELETOR = "#cpf_cnpj, input[type='text']"
