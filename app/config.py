"""Configurações e caminhos do projeto."""
from pathlib import Path

# Raiz do projeto (pasta seazone-dd)
RAIZ = Path(__file__).resolve().parent.parent

# Onde os PDFs das certidões são salvos (uma subpasta por franquia)
PASTA_SAIDA = RAIZ / "dados" / "saida"

# Onde ficam os PDFs de processos que você baixa para o sistema ler
PASTA_PROCESSOS = RAIZ / "dados" / "processos"

# Perfil persistente do navegador: mantém logins/cookies entre execuções
# (útil para sites que exigem cadastro, como o CENPROT, e para o certificado).
PASTA_PERFIL = RAIZ / "dados" / "perfil_navegador"

# Mostrar o navegador durante a automação?
# Precisa ser True para você conseguir resolver os captchas.
NAVEGADOR_VISIVEL = True

for _p in (PASTA_SAIDA, PASTA_PROCESSOS, PASTA_PERFIL):
    _p.mkdir(parents=True, exist_ok=True)

# --- Certificado digital (login automático nos sites que exigem) ---
# CERT_PFX/CERT_SENHA vêm de config_local.py (fora do Git). Sem ele, fica desativado.
try:
    from .config_local import CERT_PFX, CERT_SENHA
except Exception:
    CERT_PFX = None
    CERT_SENHA = None

# Token da API do Portal da Transparência (checagem de PEP) — vem de config_local.
try:
    from .config_local import PORTAL_TOKEN
except Exception:
    PORTAL_TOKEN = None

# Sites que podem pedir login por certificado (origens exatas para o navegador)
CERT_ORIGINS = [
    "https://cav.receita.fazenda.gov.br",
    "https://certificado.sso.acesso.gov.br",
    "https://sso.acesso.gov.br",
    "https://www.pesquisaprotesto.com.br",
    "https://certidoes.tjsc.jus.br",
    "https://esaj.tjsp.jus.br",
    "https://portalcertidoes.tjba.jus.br",
]
