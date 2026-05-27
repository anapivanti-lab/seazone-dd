"""Configurações e caminhos do projeto."""
from pathlib import Path

# Raiz do projeto (pasta seazone-dd)
RAIZ = Path(__file__).resolve().parent.parent

# Pasta opcional do Google Drive (para Desktop). Se definida no config_local e
# se o caminho EXISTIR, cada DD é salva lá e sincroniza sozinha; senão, local.
try:
    from .config_local import PASTA_SAIDA_DRIVE
except Exception:
    PASTA_SAIDA_DRIVE = None

_PASTA_LOCAL = RAIZ / "dados" / "saida"


def base_saida() -> Path:
    """Resolve a pasta-base das DDs a cada uso (assim, se você ligar o Drive no
    meio do caminho, novas DDs já vão para lá sem reiniciar)."""
    if PASTA_SAIDA_DRIVE:
        alvo = Path(PASTA_SAIDA_DRIVE)
        if alvo.exists():  # só usa o Drive se a pasta realmente já estiver lá
            return alvo
    _PASTA_LOCAL.mkdir(parents=True, exist_ok=True)
    return _PASTA_LOCAL


# Onde os PDFs das certidões são salvos (uma subpasta por franquia)
PASTA_SAIDA = base_saida()

# Onde ficam os PDFs de processos que você baixa para o sistema ler
PASTA_PROCESSOS = RAIZ / "dados" / "processos"

# Perfil persistente do navegador: mantém logins/cookies entre execuções
# (útil para sites que exigem cadastro, como o CENPROT, e para o certificado).
PASTA_PERFIL = RAIZ / "dados" / "perfil_navegador"

# Mostrar o navegador durante a automação?
# Precisa ser True para você conseguir resolver os captchas.
NAVEGADOR_VISIVEL = True

for _p in (PASTA_PROCESSOS, PASTA_PERFIL):
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

# E-mail para certidões que só são enviadas por e-mail (alguns sites não baixam direto)
EMAIL_CERTIDOES = "ana.pivanti@seazone.com.br"
