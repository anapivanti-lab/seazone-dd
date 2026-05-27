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

echo [3/3] Instalando o navegador da automacao (Chromium)...
".venv\Scripts\python.exe" -m playwright install chromium

echo.
echo ============================================
echo   Instalacao concluida!
echo   Agora rode o arquivo  iniciar.bat
echo ============================================
pause
