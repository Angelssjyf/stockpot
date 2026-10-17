@echo off
REM ==============================================================
REM  StockPot - Publica la app en internet con ngrok.
REM  - Servidor de produccion Waitress (SIN modo debug: es seguro exponerlo).
REM  - Enlace publico de ngrok para compartir con el equipo o el docente.
REM  Uso: doble clic. Para dejar de publicar: cierra las dos ventanas.
REM ==============================================================
title StockPot - ngrok
cd /d "%~dp0backend"

if not exist ".venv\Scripts\waitress-serve.exe" (
    echo [ERROR] Falta Waitress. Ejecuta en backend:  pip install -r requirements.txt
    pause
    exit /b 1
)
if not exist ".env" (
    echo [ERROR] Falta el archivo backend\.env.
    pause
    exit /b 1
)
if not exist "..\mobile\build\web\index.html" (
    echo [ERROR] La app web no esta compilada: ejecuta  compilar-app.bat  primero.
    pause
    exit /b 1
)
netstat -ano | findstr ":5000 " | findstr "LISTENING" >nul
if not errorlevel 1 (
    echo [ERROR] El puerto 5000 ya esta en uso. Cierra la ventana de iniciar.bat
    echo         o cualquier otro servidor de StockPot y vuelve a intentarlo.
    pause
    exit /b 1
)

REM Dominio fijo opcional: escribelo en el archivo ngrok-dominio.txt (junto a este .bat)
set "DOMINIO="
if exist "%~dp0ngrok-dominio.txt" set /p DOMINIO=<"%~dp0ngrok-dominio.txt"

echo Iniciando el servidor de StockPot (Waitress, sin debug)...
start "StockPot - servidor publico" cmd /k ".venv\Scripts\waitress-serve.exe --host=127.0.0.1 --port=5000 --call app:create_app"
timeout /t 3 /nobreak >nul

echo.
echo ================================================================
echo  Comparte el enlace https://... que aparece en "Forwarding".
echo  Para dejar de publicar: cierra esta ventana y la del servidor.
echo ================================================================
echo.
if defined DOMINIO (
    ngrok http --url=%DOMINIO% 5000
) else (
    ngrok http 5000
)
pause
