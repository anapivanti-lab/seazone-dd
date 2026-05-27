@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   Instalando o sistema de Due Diligence
echo ============================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo [ERRO] Python nao encontrado.
    echo Instale o Python 3.12 em https://www.python.org/downloads/
    echo IMPORTANTE: marque a opcao "Add python.exe to PATH" durante a instalacao.
    pause
    exit /b 1
)

if not exist ".venv" (
    echo [1/3] Criando ambiente Python isolado...
    py -m venv .venv
)

echo [2/3] Instalando bibliotecas (pode demorar alguns minutos)...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt

echo [3/4] Instalando o navegador da automacao (Chromium)...
".venv\Scripts\python.exe" -m playwright install chromium

echo [4/4] Baixando o pacote de portugues do leitor (OCR de documentos)...
if not exist "dados\tessdata" mkdir "dados\tessdata"
if not exist "dados\tessdata\por.traineddata" (
    powershell -NoProfile -Command "try { Invoke-WebRequest 'https://github.com/tesseract-ocr/tessdata/raw/main/por.traineddata' -OutFile 'dados\tessdata\por.traineddata' -UseBasicParsing } catch { Write-Host '[aviso] Nao consegui baixar o portugues do OCR; a leitura usara ingles.' }"
)
if not exist "dados\tessdata\eng.traineddata" if exist "C:\Program Files\Tesseract-OCR\tessdata\eng.traineddata" copy "C:\Program Files\Tesseract-OCR\tessdata\eng.traineddata" "dados\tessdata\eng.traineddata" >nul

echo [5/5] (Opcional) IA local para resumir processos em linguagem simples (Ollama)...
where winget >nul 2>nul && (
    where ollama >nul 2>nul || winget install --id Ollama.Ollama -e --silent --accept-package-agreements --accept-source-agreements
    powershell -NoProfile -Command "$env:Path += ';' + $env:LOCALAPPDATA + '\Programs\Ollama'; try { ollama pull llama3.2:3b } catch { Write-Host '[aviso] Sem a IA local o sistema usa o resumo por regras (funciona normal).' }"
) || echo [aviso] winget ausente — IA local opcional nao instalada (o sistema usa resumo por regras).

echo.
echo ============================================
echo   Instalacao concluida!
echo   Agora rode o arquivo  iniciar.bat
echo ============================================
pause
