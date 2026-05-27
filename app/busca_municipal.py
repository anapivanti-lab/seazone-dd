"""Acha o site oficial da CND Municipal (certidão negativa de débitos do
município) a partir do nome da cidade. Usa busca gratuita (DuckDuckGo HTML) +
heurística para priorizar o domínio oficial (.gov.br / prefeitura). Sempre
devolve também um link de BUSCA do Google pronto, como reserva infalível.
"""
from __future__ import annotations

import html
import re
import unicodedata
import urllib.parse

import httpx

_cache: dict[str, dict] = {}

_KW_BONS = ("certid", "cnd", "tribut", "negativa", "iss", "mobiliar",
            "fazend", "contribuinte", "debito", "débito", "emiss", "emitir")
_DOMINIOS_RUINS = ("wikipedia", "jusbrasil", "google.", "bing.", "facebook",
                   "youtube", "instagram", "globo", "uol.", "g1.", "reclameaqui",
                   "linkedin", "twitter", "duckduckgo")
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def _norm(s: str) -> str:
    s = (s or "").strip().lower()
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def google_url(cidade: str, uf: str = "") -> str:
    q = f"CND certidão negativa débitos municipais {cidade} {uf} prefeitura emitir"
    return "https://www.google.com/search?q=" + urllib.parse.quote(q.strip())


def _parse_ddg(texto: str) -> list[dict]:
    achados = []
    for m in re.finditer(r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', texto, re.S):
        href = html.unescape(m.group(1))
        titulo = html.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip()
        if "uddg=" in href:  # link de redirecionamento do DDG -> extrai o destino real
            params = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
            if params.get("uddg"):
                href = params["uddg"][0]
        if href.startswith("//"):
            href = "https:" + href
        if href.startswith("http"):
            achados.append({"url": href, "titulo": titulo})
    return achados


def buscar(cidade: str, uf: str = "") -> dict:
    cidade = (cidade or "").strip()
    if not cidade:
        return {"ok": False}
    chave = _norm(cidade) + "|" + _norm(uf)
    if chave in _cache:
        return _cache[chave]

    res = {"ok": True, "cidade": cidade, "uf": uf, "url": None, "titulo": "",
           "alternativas": [], "google": google_url(cidade, uf)}
    cidade_slug = _norm(cidade).replace(" ", "")

    def score(item: dict) -> int:
        u = item["url"].lower()
        t = _norm(item["titulo"])
        host = urllib.parse.urlparse(u).netloc.lower()
        if any(b in host for b in _DOMINIOS_RUINS):
            return -100
        s = 0
        if ".gov.br" in host:
            s += 5
        if "prefeitura" in host or "pmf" in host:
            s += 2
        if cidade_slug[:6] and cidade_slug[:6] in host.replace("-", "").replace(".", ""):
            s += 3
        s += sum(1 for k in _KW_BONS if k in u or k in t)
        return s

    try:
        q = f"certidão negativa de débitos municipais {cidade} {uf} prefeitura emitir"
        r = httpx.post("https://html.duckduckgo.com/html/", data={"q": q},
                       headers={"User-Agent": _UA, "Accept-Language": "pt-BR,pt"}, timeout=12,
                       follow_redirects=True)
        achados = _parse_ddg(r.text)
        bons = [a for a in achados if score(a) > -50]
        bons.sort(key=score, reverse=True)
        if bons and score(bons[0]) >= 4:
            res["url"] = bons[0]["url"]
            res["titulo"] = bons[0]["titulo"]
        res["alternativas"] = [a["url"] for a in bons[:4]]
    except Exception:
        pass

    _cache[chave] = res
    return res
