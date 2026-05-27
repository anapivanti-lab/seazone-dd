"""Diagnóstico de calibração: abre cada site e diz se o endereço responde.

Uso (a partir da pasta do projeto):
    .venv\\Scripts\\python.exe -m app.diagnostico

Serve para conferir rapidamente se as URLs estão corretas (sem 421/404),
sem precisar resolver captcha.
"""
import asyncio

from playwright.async_api import async_playwright

from .models import Contexto, TipoPessoa
from .providers import provedores_para


async def main():
    ctx = Contexto(tipo=TipoPessoa.PJ, documento="00000000000191")
    provs = provedores_para(ctx)
    async with async_playwright() as pw:
        navegador = await pw.chromium.launch(headless=True)
        for p in provs:
            page = await navegador.new_page()  # aba nova por site (isola falhas)
            url = p.url(ctx)
            try:
                resp = await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                status = resp.status if resp else "?"
                titulo = (await page.title())[:70]
                print(f"[{status}] {p.nome}\n      {url}\n      titulo: {titulo}\n")
            except Exception as e:
                msg = str(e).splitlines()[0]
                print(f"[ERRO] {p.nome}\n      {url}\n      {type(e).__name__}: {msg}\n")
            finally:
                await page.close()
        await navegador.close()


if __name__ == "__main__":
    asyncio.run(main())
