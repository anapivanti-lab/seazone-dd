# MODELO de configuração local.
# Copie este arquivo para  app/config_local.py  e preencha com os seus dados.
# O arquivo app/config_local.py NÃO vai para o Git (está no .gitignore).
# Tudo aqui é OPCIONAL: sem isso o sistema funciona, só não usa certificado/PEP.

# 1) Certificado digital A1 (.pfx) da empresa, em formato moderno (AES).
#    Depois de instalar o .pfx no Windows (2 cliques), gere a versão moderna:
#      $c = Get-Item Cert:\CurrentUser\My\<THUMBPRINT>
#      Export-PfxCertificate -Cert $c -FilePath cert.pfx `
#        -Password (Read-Host -AsSecureString) -CryptoAlgorithmOption AES256_SHA256
CERT_PFX = r"C:\caminho\para\cert.pfx"
CERT_SENHA = "senha-do-certificado"

# 2) Token gratuito da API do Portal da Transparência (checagem de PEP).
#    Gere em: https://api.portaldatransparencia.gov.br/api-de-dados/cadastrar-email
PORTAL_TOKEN = "seu-token-aqui"
