"""CND Estadual da Bahia (SEFAZ-BA) — sem captcha e sem login, então o sistema
emite e baixa o PDF 100% sozinho (headless), sem você fazer nada."""
from ..base import BaseProvider, registrar
from ..util import caminho_saida, salvar_download
from ...models import TipoPessoa


@registrar
class SefazBA(BaseProvider):
    nome = "CND Estadual (Fazenda) — BA"
    nome_arquivo = "CND_Estadual_BA"
    ufs = ["BA"]
    auto_completo = True
    URL = "https://servicos.sefaz.ba.gov.br/sistemas/DSCRE/Modulos/Publico/EmissaoCertidao.aspx"

    async def executar(self, ctx, page):
        await page.goto(self.URL, wait_until="domcontentloaded", timeout=60000)
        campo = "#PHConteudo_TxtNumCNPJ" if ctx.tipo == TipoPessoa.PJ else "#PHConteudo_TxtNumCPF"
        await page.fill(campo, ctx.documento)
        # Tenta emitir/imprimir e capturar o PDF baixado
        try:
            async with page.expect_download(timeout=25000) as dl:
                await page.click("#PHConteudo_btnImprimir")
            return await salvar_download(await dl.value, ctx, self.nome_arquivo)
        except Exception:
            # Sem download: salva a página da certidão como PDF (só funciona headless)
            await page.wait_for_timeout(2500)
            destino = caminho_saida(ctx, self.nome_arquivo, "pdf")
            await page.pdf(path=str(destino), format="A4")
            return destino
