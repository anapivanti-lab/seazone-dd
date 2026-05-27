@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Ambiente nao encontrado. Rode primeiro o  instalar.bat
    pause
    exit /b 1
)

echo Iniciando o sistema...
echo A tela vai abrir no seu navegador em alguns segundos: http://127.0.0.1:8000
echo (Para encerrar, feche esta janela.)

REM Abre o navegador depois de 3 segundos, dando tempo do servidor subir
start "" /min cmd /c "timeout /t 3 /nobreak >nul & start http://127.0.0.1:8000"

".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
