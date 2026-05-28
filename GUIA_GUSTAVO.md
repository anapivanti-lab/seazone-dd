# Guia de instalação — Sistema de DD de Franquias

Olá, Gustavo! Esse guia te leva do zero ao sistema funcionando em **uns 30 minutos**.

É só seguir os passos na ordem. Onde tiver dúvida, manda mensagem pra Ana.

---

## ⚠️ Antes de começar

Você precisa ter em mãos **três coisas que a Ana vai te enviar** (provavelmente por WhatsApp ou e-mail — **não pelo GitHub**, porque são arquivos sensíveis):

1. O arquivo **`cert_seazone.pfx`** (certificado digital da Seazone)
2. A **senha do certificado**
3. O **token do Portal da Transparência** (uma sequência tipo `86bf17c611df3cfe31a2ff823f188c04`)

Guarda esses 3 itens num lugar fácil de achar. A gente vai usar no Passo 5.

---

## Passo 1 — Instalar o Python (uma vez só)

1. Abre esse link no navegador: https://www.python.org/downloads/
2. Clica no botão amarelo grande **"Download Python 3.12"** (ou versão mais nova).
3. Quando o arquivo terminar de baixar, dá **dois cliques** nele.
4. **MUITO IMPORTANTE:** na primeira tela do instalador, marca a caixinha **"Add python.exe to PATH"** (fica embaixo). Se você não marcar, o sistema não vai funcionar.
5. Clica em **"Install Now"** e espera terminar.
6. Quando aparecer "Setup was successful", fecha.

---

## Passo 2 — Baixar o sistema

1. Pede pra Ana te adicionar como colaborador no GitHub. Ela tem que ir em https://github.com/anapivanti-lab/seazone-dd/settings/access e te convidar pelo seu usuário do GitHub.
2. Você vai receber um e-mail de convite — aceita.
3. Abre https://github.com/anapivanti-lab/seazone-dd
4. Clica no botão verde **"Code"** → **"Download ZIP"**.
5. O arquivo `seazone-dd-main.zip` cai na pasta Downloads.
6. Clica com o **botão direito** nele → **"Extrair tudo..."** → escolhe extrair em **`C:\`** (ou seja, a raiz do disco C).
7. No final, você deve ter uma pasta chamada **`C:\seazone-dd-main`** (ou parecida). Renomeia ela para **`C:\seazone-dd`** (mais simples).

---

## Passo 3 — Rodar o instalador

1. Abre a pasta **`C:\seazone-dd`**.
2. Acha o arquivo **`instalar.bat`** e dá **dois cliques** nele.
3. Vai abrir uma janela preta com várias mensagens passando. **Não fecha.** Pode demorar uns **15 a 20 minutos** (ele baixa um monte de coisa: bibliotecas, navegador, Tesseract pra OCR, Ollama pra IA local).
4. Quando aparecer **"Instalação concluída"** ou a janela parar e mostrar "Pressione qualquer tecla para sair", terminou. Pode fechar.

> Se der algum erro vermelho no meio, tira print da tela e manda pra Ana antes de continuar.

---

## Passo 4 — Colocar o certificado no lugar

1. Pega o arquivo **`cert_seazone.pfx`** que a Ana te mandou.
2. **Cola ele dentro da pasta `C:\seazone-dd`** (no mesmo lugar do `instalar.bat`).
3. Agora você vai instalar o certificado no Windows também:
   - Dá **dois cliques** no `cert_seazone.pfx`.
   - Aparece um assistente. Clica em **"Avançar"** até pedir a senha.
   - Cola a senha que a Ana te mandou. Clica em **"Avançar"** até terminar.
   - Mantém marcado **"Usuário Atual"** (não "Computador Local").
   - Quando aparecer "A importação obteve êxito", clica em OK.

---

## Passo 5 — Configurar os "segredos" do sistema

1. Dentro da pasta **`C:\seazone-dd`**, acha o arquivo **`config_local.example.py`**.
2. **Copia ele e cola na mesma pasta** (vai criar um chamado `config_local.example - Copia.py`).
3. Move essa cópia pra dentro da subpasta **`app`** (`C:\seazone-dd\app`).
4. Renomeia a cópia que está em `app` para **`config_local.py`** (sem o `.example` e sem o `- Copia`).
5. Clica com o botão direito nesse arquivo → **"Abrir com" → "Bloco de Notas"**.
6. Preenche as três linhas:
   - `CERT_PFX = r"C:\seazone-dd\cert_seazone.pfx"`
   - `CERT_SENHA = "cola_aqui_a_senha_que_a_ana_mandou"`
   - `PORTAL_TOKEN = "cola_aqui_o_token_que_a_ana_mandou"`
7. **Salva** (Ctrl+S) e fecha.

---

## Passo 6 — Ligar o sistema pela primeira vez

1. Volta na pasta **`C:\seazone-dd`**.
2. Dá **dois cliques** em **`iniciar.bat`**.
3. Vai abrir uma janela preta (deixa ela aberta — é o "motor" do sistema) e logo em seguida o navegador abre em **http://127.0.0.1:8000**.
4. **Pronto.** O sistema é igualzinho ao da Ana.

Pra usar no dia a dia, sempre é só clicar no `iniciar.bat`. Pra desligar, fecha a janela preta.

> Dica: pra ficar mais prático, clica com botão direito no `iniciar.bat` → "Enviar para" → "Área de Trabalho (criar atalho)". Renomeia o atalho pra **"DD Franquias - Iniciar"**.

---

## Passo 7 — Conectar com o Drive da Seazone (pra os arquivos irem pro lugar certo)

Esse passo só vale se você quiser que as DDs que VOCÊ fizer caiam na mesma pasta do Drive que a Ana usa.

1. Confere se você tem o **Google Drive para Desktop** instalado e logado com a sua conta `@seazone.com.br`. Se não tiver: https://www.google.com/drive/download/
2. Confere se você consegue ver a pasta **Franquias** (que fica em `08-Jurídico / TESTE 2 / 26. Due Diligences / Franquias`). Se não conseguir, pede pra Ana compartilhar.
3. Adiciona um **atalho** dessa pasta no "Meu Drive" (botão direito → "Adicionar atalho ao Drive").
4. Avisa a Ana — ela te passa a configuração exata do caminho `PASTA_SAIDA_DRIVE` pra colocar no seu `config_local.py`.

Se você pular esse passo, o sistema ainda funciona — só vai salvar tudo numa pasta local (`C:\seazone-dd\dados\saidas\...`) em vez de direto no Drive.

---

## Deu problema?

- **Janela preta fecha sozinha quando clico em `iniciar.bat`:** o Python provavelmente não foi instalado direito (esqueceu de marcar "Add to PATH"). Desinstala e reinstala marcando a caixinha.
- **"ModuleNotFoundError" ou erro vermelho:** roda o `instalar.bat` de novo.
- **Site abre mas tá com erro de certificado:** confere se o `cert_seazone.pfx` está na pasta `C:\seazone-dd` e se a senha em `config_local.py` está exata (sem espaços antes/depois).
- **Qualquer outra coisa:** print da tela inteira (com a janela preta visível) e manda pra Ana.

---

Bom trabalho! 🚀
