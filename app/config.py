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
