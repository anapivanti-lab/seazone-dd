# Guia de instalação — Sistema de DD de Franquias

Olá, Gustavo! Esse guia te leva do zero ao sistema funcionando em **uns 45 a 60 minutos** (contando uma pausa pra esperar o instalador baixar tudo).

É só seguir os passos na ordem. Onde tiver dúvida, manda mensagem pra Ana.

> :information_source: **Boa notícia:** o sistema **funciona mesmo sem o certificado e os tokens**. Se você quiser só ver ele rodando primeiro, pode pular os Passos 4 e 5 — depois você volta e completa. Mas se vai usar pra valer, faz tudo na ordem.

---

## :warning: Antes de começar — manda essa mensagem pra Ana

Pra não te travar no meio do caminho, manda essa mensagem **agora** pra Ana e vai começando o Passo 1 enquanto ela responde:

> "Oi Ana, vou começar a instalação do sistema de DD de Franquias. Preciso de:
>
> 1. O arquivo **`cert_seazone.pfx`** (certificado digital da Seazone)
> 2. A **senha do certificado** (de preferência sem usar `"` ou `\` na senha — quebra a configuração)
> 3. O **token do Portal da Transparência** (sequência tipo `86bf17c611df3cfe31a2ff823f188c04`)
> 4. A configuração do **`PASTA_SAIDA_DRIVE`** (caminho do Google Drive onde as DDs ficam salvas)
> 5. Me adicionar como colaborador no GitHub do projeto — meu usuário é: **_______________**
>
> Ah, se eu ainda não tenho conta no GitHub: vou criar em github.com com meu e-mail Seazone e te mando o usuário."

> :information_source: **Como mandar:** WhatsApp ou e-mail. **Não pelo GitHub**, porque são arquivos sensíveis.

Quando ela te responder com tudo, guarda os 3 arquivos/senhas num lugar fácil de achar. A gente vai usar nos Passos 4, 5 e 7.

---

## Passo 1 — Instalar o Python (uma vez só)

1. Abre esse link no navegador: https://www.python.org/downloads/
2. Clica no botão grande de download que aparece no topo da página (vai dizer algo como **"Download Python 3.12.x"** ou versão mais nova — pode ser amarelo, azul, depende da versão atual).
3. Quando o arquivo terminar de baixar, dá **dois cliques** nele.
4. **MUITO IMPORTANTE:** na primeira tela do instalador, marca a caixinha **"Add python.exe to PATH"** (fica embaixo). Se você não marcar, o sistema não vai funcionar.
5. Clica em **"Install Now"** e espera terminar.
6. Quando aparecer "Setup was successful", fecha.

### Confere se instalou direito (30 segundos)

1. Aperta a tecla **Windows** e digita **`cmd`**.
2. Abre o "Prompt de Comando" (janela preta).
3. Digita: `py --version` e aperta **Enter**.
4. Se aparecer **"Python 3.12.x"** (ou parecido), tá perfeito. Fecha a janela e segue.
5. Se aparecer **"py não é reconhecido como um comando"**: desinstala o Python (Iniciar → Apps → Python → Desinstalar) e reinstala marcando **"Add python.exe to PATH"**.

---

## Passo 2 — Baixar o sistema

1. Já pediu pra Ana te adicionar como colaborador? Você deve ter recebido um e-mail de convite. **Aceita o convite.**
   - Se você ainda não tem conta no GitHub: cria em https://github.com/signup com seu e-mail Seazone, manda seu usuário pra Ana, e espera ela adicionar.
2. Abre https://github.com/anapivanti-lab/seazone-dd
3. Clica no botão verde **"Code"** → **"Download ZIP"**.
4. O arquivo `seazone-dd-main.zip` cai na pasta Downloads.
5. Clica com o **botão direito** nele → **"Extrair tudo..."** (no Windows 11 pode estar em "Mostrar mais opções") → escolhe extrair em **`C:\`** (a raiz do disco C, **não** dentro de Documentos nem do OneDrive).
6. No final, você deve ter uma pasta chamada **`C:\seazone-dd-main`** (ou parecida). Renomeia ela para **`C:\seazone-dd`**:
   - Clica com botão direito na pasta → "Renomear" → digita `seazone-dd` → Enter.

> :warning: **Cuidado com o OneDrive:** se sua pasta Documentos sincroniza com OneDrive, NÃO extrai lá dentro. O sistema espera o caminho exato `C:\seazone-dd` — qualquer coisa diferente quebra.

---

## Passo 3 — Rodar o instalador

1. Abre a pasta **`C:\seazone-dd`**.
2. Acha o arquivo **`instalar.bat`** e dá **dois cliques** nele.
3. **Se aparecer uma tela azul "O Windows protegeu seu PC":** clica em **"Mais informações"** → **"Executar assim mesmo"**. Isso é o SmartScreen sendo cauteloso com arquivos baixados da internet — o `instalar.bat` é confiável (vem do repo da Ana).
4. Vai abrir uma janela preta com várias mensagens passando. **Não fecha.** Pode demorar uns **15 a 25 minutos** (ele cria o ambiente Python, baixa as bibliotecas, o navegador da automação e a IA local). Aproveita pra tomar um café.
5. Quando aparecer **"Instalação concluída!"** e a mensagem "Pressione qualquer tecla para sair", terminou. Pode fechar.

> Se der algum erro vermelho no meio, tira print da tela inteira e manda pra Ana antes de continuar.

> :information_source: **Se aparecer "[aviso] winget ausente" ou "[aviso] Sem a IA local":** relaxa, é avisinho, não é erro. O sistema funciona normal sem a IA local — ela só serve pra resumir processos em linguagem simples.

---

## Passo 4 — Colocar o certificado no lugar (opcional)

> **Esse passo é opcional.** O sistema funciona sem certificado — só não consegue acessar sites que pedem login (CENPROT, certidões judiciais). Pra valer, faz.

1. Pega o arquivo **`cert_seazone.pfx`** que a Ana te mandou.
2. **Cola ele dentro da pasta `C:\seazone-dd`** (no mesmo lugar do `instalar.bat`).
3. Agora você vai instalar o certificado no Windows também (alguns serviços do sistema usam o certificado armazenado no Windows, não só o arquivo da pasta):
   - Dá **dois cliques** no `cert_seazone.pfx` que está em `C:\seazone-dd`.
   - Aparece um assistente. Clica em **"Avançar"** até pedir a senha.
   - Cola a senha que a Ana te mandou. Clica em **"Avançar"** até terminar.
   - Mantém marcado **"Usuário Atual"** (não "Computador Local").
   - Quando aparecer "A importação obteve êxito", clica em OK.

---

## Passo 5 — Configurar os "segredos" do sistema (opcional)

> **Esse passo também é opcional.** Pode ser feito depois. Sem ele, o sistema roda sem certificado/checagem de PEP.

### 5a. Antes de tudo: ativa a visualização de extensões de arquivo

Isso é **crítico** — se você pular, o próximo passo vai criar um arquivo `config_local.py.py` por engano (com `.py` duplicado, invisível) e o sistema não vai achar.

1. Abre o **Explorador de Arquivos** (qualquer pasta).
2. No menu de cima, clica em **"Exibir"** (no Windows 11, pode estar dentro de "Ver" ou "Mostrar").
3. **Marca a caixinha "Extensões de nome de arquivo"** (no Windows 10) ou **"Extensões de nomes de arquivos"** (no Windows 11, dentro de "Mostrar").
4. Agora você consegue ver `.py` no final dos arquivos. Pode seguir.

### 5b. Criar o `config_local.py` dentro de `app/`

1. Vai em **`C:\seazone-dd`** e localiza o arquivo **`config_local.example.py`** (está na raiz da pasta).
2. **Copia ele** (clica com botão direito → Copiar).
3. Entra na subpasta **`app`** (caminho: `C:\seazone-dd\app`) e **cola** (botão direito → Colar).
4. Dentro de `C:\seazone-dd\app`, clica com botão direito no arquivo colado → **"Renomear"** → apaga o `.example` do nome, deixando **`config_local.py`** (confere que terminou com `.py`, não `.py.py`).
5. Clica com o botão direito no `config_local.py` → **"Abrir com" → "Bloco de Notas"**.
6. O arquivo já vem com linhas de exemplo. **Substitui os valores** (sem mexer no nome da variável):
   - `CERT_PFX = r"C:\seazone-dd\cert_seazone.pfx"`
   - `CERT_SENHA = "cola_aqui_a_senha_que_a_ana_mandou"`
   - `PORTAL_TOKEN = "cola_aqui_o_token_que_a_ana_mandou"`
7. **Salva** (Ctrl+S) e fecha.

> :information_source: O `r` antes das aspas em `CERT_PFX` é proposital — não mexa. Ele diz pro Python ler o caminho literalmente, sem se confundir com as barras invertidas do Windows.

> :warning: **Se o certificado da Ana for antigo (formato não-AES):** alguns sites podem rejeitar. O arquivo `config_local.example.py` tem um comentário com um comando PowerShell pra converter — se acontecer problema, pede ajuda pra Ana.

---

## Passo 6 — Ligar o sistema pela primeira vez

1. Volta na pasta **`C:\seazone-dd`**.
2. Dá **dois cliques** em **`iniciar.bat`**.
3. **Se aparecer a tela azul "O Windows protegeu seu PC" de novo:** clica em **"Mais informações"** → **"Executar assim mesmo"**.
4. Vai abrir uma janela preta (deixa ela aberta — é o "motor" do sistema) e logo em seguida o navegador abre em **http://127.0.0.1:8000**.
5. **Pronto.** O sistema é igualzinho ao da Ana.

Pra usar no dia a dia, sempre é só clicar no `iniciar.bat`. Pra desligar, fecha a janela preta.

> :bulb: **Dica:** pra ficar mais prático, clica com botão direito no `iniciar.bat` → "Enviar para" → "Área de Trabalho (criar atalho)". Renomeia o atalho pra **"DD Franquias - Iniciar"**.

---

## Passo 7 — Conectar com o Drive da Seazone (pra os arquivos irem pro lugar certo)

Esse passo só vale se você quiser que as DDs que VOCÊ fizer caiam na mesma pasta do Drive que a Ana usa. **Sem isso, o sistema salva tudo em `C:\seazone-dd\dados\saida\...`** (local na sua máquina).

1. Confere se você tem o **Google Drive para Desktop** instalado e logado com a sua conta `@seazone.com.br`. Se não tiver: https://www.google.com/drive/download/
2. Confere se você consegue ver a pasta **Franquias** (que fica em `08-Jurídico / TESTE 2 / 26. Due Diligences / Franquias`). Se não conseguir, pede pra Ana compartilhar.
3. Adiciona um **atalho** dessa pasta no "Meu Drive" (botão direito → "Adicionar atalho ao Drive").
4. Abre o `config_local.py` (`C:\seazone-dd\app\config_local.py`) no Bloco de Notas e **adiciona uma linha nova no fim** com o caminho que a Ana te passou:
   - `PASTA_SAIDA_DRIVE = r"G:\Meu Drive\...\Franquias"` (a Ana te passa o caminho exato)
5. Salva (Ctrl+S) e fecha.
6. **Fecha a janela preta do `iniciar.bat` se estiver aberta e abre de novo** — o sistema precisa reler a configuração.

---

## Deu problema?

- **Tela azul "O Windows protegeu seu PC" quando clico em `instalar.bat` ou `iniciar.bat`:** clica em **"Mais informações"** → **"Executar assim mesmo"**. É só o SmartScreen sendo cauteloso.
- **Janela preta fecha sozinha quando clico em `iniciar.bat`:** o Python provavelmente não foi instalado direito (esqueceu de marcar "Add to PATH"). Roda o teste do Passo 1 (`py --version` no Prompt de Comando) pra confirmar. Se não funcionar, desinstala e reinstala marcando a caixinha.
- **"Ambiente não encontrado. Rode primeiro o instalar.bat":** é exatamente isso. Você pulou o Passo 3 — volta e roda o `instalar.bat`.
- **"ModuleNotFoundError" ou erro vermelho ao iniciar:** roda o `instalar.bat` de novo.
- **Site abre mas tá com erro de certificado:** confere se o `cert_seazone.pfx` está na pasta `C:\seazone-dd` e se a senha em `config_local.py` está exata (sem espaços antes/depois das aspas). Se a Ana avisou que o cert é antigo, pede pra ela converter pra formato AES.
- **Navegador abre em http://127.0.0.1:8000 mas mostra "Esta página não está funcionando":** espera uns 10 segundos e dá F5. O motor do sistema demora pra subir na primeira execução.
- **Não acho o arquivo `config_local.py` depois de criar:** provavelmente você criou `config_local.py.py` sem perceber. Volta no Passo 5a, ativa a visualização de extensões, e renomeia.
- **As DDs não estão indo pro Drive, só pra pasta local:** confere se (a) o Google Drive Desktop tá rodando, (b) o atalho da pasta Franquias tá no seu "Meu Drive", (c) a linha `PASTA_SAIDA_DRIVE` no `config_local.py` aponta pra um caminho que **existe agora** na sua máquina, (d) você fechou e abriu o `iniciar.bat` depois de editar.
- **Quero usar a leitura de RG/CNH (OCR) e tá dando erro:** o instalador não baixa o programa Tesseract automaticamente. Abre o Prompt de Comando como administrador e roda `winget install UB-Mannheim.TesseractOCR` (ou baixa em https://github.com/UB-Mannheim/tesseract/wiki). Sem Tesseract, é só digitar os campos do RG na mão — o resto do sistema funciona normal.
- **Antivírus (Avast, Norton, etc) bloqueia algum arquivo:** abre o antivírus, libera a pasta `C:\seazone-dd` inteira como exceção, e roda `instalar.bat` de novo.
- **O sistema diz que não acha a pasta `C:\seazone-dd`:** confere se você extraiu o ZIP em `C:\` direto, **não** dentro de Documentos ou OneDrive. Se estiver no lugar errado, recorta a pasta e move pra `C:\`.
- **Qualquer outra coisa:** print da tela inteira (com a janela preta visível) e manda pra Ana.

---

Bom trabalho! :rocket:
