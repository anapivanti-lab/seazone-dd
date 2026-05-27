"""Configurações e caminhos do projeto."""
from pathlib import Path

# Raiz do projeto (pasta seazone-dd)
RAIZ = Path(__file__).resolve().parent.parent

# Onde os PDFs das certidões são salvos (uma subpasta por franquia)
PASTA_SAIDA = RAIZ / "dados" / "saida"

# Onde ficam os PDFs de processos que você baixa para o sistema ler
PASTA_PROCESSOS = RAIZ / "dados" / "processos"

# Mostrar o navegador durante a automação?
# Precisa ser True para você conseguir resolver os captchas.
NAVEGADOR_VISIVEL = True

# Tempo máximo (segundos) que o sistema espera você resolver um captcha
# e a certidão ser gerada antes de seguir para a próxima.
TIMEOUT_CAPTCHA = 180

PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
PASTA_PROCESSOS.mkdir(parents=True, exist_ok=True)
