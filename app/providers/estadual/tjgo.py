"""Certidão da Justiça Estadual de Goiás (TJGO/Projudi) — antecedentes criminais.
Formulário de pessoa física (sem captcha): preenche Nome, CPF, Nome da Mãe e
Data de Nascimento. Por isso depende dos 'Dados adicionais' preenchidos."""
from ..base import BaseProvider, registrar

URL = ("https://projudi.tjgo.jus.br/CertidaoNegativaPositivaPublica"
       "?PaginaAtual=1&TipoArea=2&InteressePessoal=S")


@registrar
class TJGOCriminal(BaseProvider):
    nome = "Justiça Estadual GO — Criminal (antecedentes)"
    nome_arquivo = "TJGO_Criminal"
    ufs = ["GO"]

    async def abrir(self, ctx, page):
        await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(2000)

        async def preencher(sel, valor):
            if valor:
                try:
                    await page.fill(sel, valor, timeout=4000)
                except Exception:
                    pass

        await preencher("#Nome", ctx.nome)
        await preencher("#Cpf", ctx.documento)
        await preencher("#NomeMae", ctx.nome_mae)
        await preencher("#DataNascimento", ctx.data_nascimento)
