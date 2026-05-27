# Sistema de Due Diligence de Franquias — Seazone

Emite automaticamente as certidões da due diligence de franquias (CNDs, certidões
judiciais, protestos, etc.), organiza tudo em uma pasta por franquia e gera um
relatório. Onde houver captcha, o sistema preenche os dados e abre a tela para
**você só resolver o captcha**.

> **Custo: R$ 0.** Usa apenas ferramentas gratuitas e de código aberto. Nenhum
> serviço pago de certidões. (A futura leitura de processos por IA também será
> gratuita — ver "Próximas etapas".)

---

## 1. Pré-requisitos (instalar uma vez)

Você só precisa do **Python 3.12 ou superior**:

1. Baixe em https://www.python.org/downloads/
2. Ao instalar, **marque a caixinha "Add python.exe to PATH"** (muito importante).

Para conferir se já tem, abra o Prompt de Comando e digite `py --version`.

## 2. Instalação (uma vez)

Dê **dois cliques** no arquivo:

```
instalar.bat
```

Ele cria o ambiente, baixa as bibliotecas e o navegador da automação. Pode
demorar alguns minutos na primeira vez. Ao terminar, aparece "Instalação concluída".

## 3. Como usar (no dia a dia)

1. Dê dois cliques em **`iniciar.bat`** (ou no atalho da Área de Trabalho).
   A tela abre sozinha no navegador (`http://127.0.0.1:8000`).
2. Escolha **Franquia (CNPJ)** ou **Operador/Representante (CPF)**, preencha o
   documento, o nome, a UF e o município. Marque as **certidões** desejadas e
   clique em **Iniciar emissão**.
3. Uma **janela de navegador** abre com uma aba por certidão, já com o documento
   preenchido. Em cada aba, **resolva o captcha** e clique em consultar/emitir.
   Cada PDF que baixar é **salvo automaticamente** na pasta da franquia.
4. Quando terminar, volte à tela e clique em **Concluir e gerar relatório**.
   Use **Abrir pasta dos PDFs** para ver os arquivos e o `relatorio.html`.

Para encerrar o sistema, feche a janela preta do `iniciar.bat`.

---

## 4. O que já funciona e o que vem (etapas)

| Etapa | Conteúdo | Status |
|-------|----------|--------|
| 1 | **Federais/nacionais**: CND Federal (Receita/PGFN), CND Trabalhista (TST), Protestos (CENPROT Nacional), Cartão CNPJ | 🟢 endereços confirmados; ajustando captcha/preenchimento |
| 2 | **SC**: Fazenda estadual, TJSC e prefeituras de SC | ⬜ a fazer |
| 3 | **BA (Salvador)** e **SP (capital)** | ⬜ a fazer |
| 4 | Demais estados + **leitor de processos** + **parecer de risco** | ⬜ a fazer |

> **"Calibrando sites":** automação de site do governo precisa de um primeiro
> teste ao vivo para acertar exatamente onde fica cada campo/botão (o HTML deles
> muda de tempos em tempos). Na primeira execução real ajustamos juntos.

---

## 5. Estrutura do projeto (para quem for testar/manter)

```
seazone-dd/
├── instalar.bat          # instala tudo (1 clique)
├── iniciar.bat           # liga o sistema (1 clique)
├── requirements.txt      # bibliotecas usadas
├── app/
│   ├── main.py           # servidor web (as telas)
│   ├── orchestrator.py   # abre o navegador e percorre as certidões
│   ├── storage.py        # cria a pasta da franquia e o relatório
│   ├── models.py         # estruturas de dados
│   ├── config.py         # caminhos e ajustes
│   ├── providers/        # UM arquivo por certidão (fácil de crescer)
│   │   ├── base.py       # base comum + fluxo "assistido" (com captcha)
│   │   ├── federal/      # CND federal, trabalhista, FGTS, protestos, cartão CNPJ
│   │   ├── estadual/     # (etapa 2+)
│   │   └── municipal/    # (etapa 2+)
│   ├── templates/        # a tela (HTML)
│   └── static/           # estilo e comportamento da tela
└── dados/
    ├── saida/            # PDFs e relatórios gerados (uma pasta por franquia)
    └── processos/        # PDFs de processos para o leitor (etapa 4)
```

### Como adicionar uma nova certidão (desenvolvedor)

Crie um arquivo em `app/providers/<nivel>/` com uma classe decorada:

```python
from ..base import BaseProvider, registrar

@registrar
class MinhaCertidao(BaseProvider):
    nome = "Nome legível da certidão"
    ufs = ["SC"]          # opcional: só aparece para essas UFs
    aplica_pf = False     # opcional: só PJ

    async def emitir(self, ctx, page):
        async def preencher(page, ctx):
            await page.locator("#campo").fill(ctx.documento)
        return await self._fluxo_assistido(page, ctx, "https://site...", "Nome_Arquivo", preencher)
```

Pronto — ela é detectada e usada automaticamente.

---

## 6. Certificado digital (sites que pedem login)

Alguns sites (CENPROT, certidões judiciais) exigem login por **certificado
digital A1** (arquivo `.pfx`). Instale o certificado **uma vez** no Windows:

- Dê **dois cliques no arquivo `.pfx`** e siga o assistente (escolha "Usuário
  Atual"), **ou** rode no PowerShell:
  `Import-PfxCertificate -FilePath "CAMINHO\cert.pfx" -CertStoreLocation Cert:\CurrentUser\My -Password (Read-Host -AsSecureString)`

Depois, ao abrir esses sites, o navegador mostra um aviso para **selecionar o
certificado** — escolha o da empresa. O arquivo `.pfx` e a senha **nunca** devem
ir para o repositório (já estão no `.gitignore`).

## 7. Leitor de identidade (OCR) — opcional

Para o sistema ler **RG, nome da mãe e data de nascimento** de uma imagem do
RG/CNH, instale o **Tesseract OCR** (gratuito):
`winget install UB-Mannheim.TesseractOCR` (ou baixe em
https://github.com/UB-Mannheim/tesseract/wiki). Sem ele, basta digitar os campos.

## 8. Avisos

- Os PDFs ficam **só na sua máquina** (`dados\saida`), não vão para a internet.
- A pasta `dados\` está fora do controle de versão (Git) por conter dados
  pessoais — nunca suba certidões reais para repositório.
