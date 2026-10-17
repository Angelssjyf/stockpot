@echo off
REM ==============================================================
REM  StockPot - Inicia todo de una vez:
REM   1. Servidor de produccion Waitress (SIN modo debug: seguro para ngrok)
REM   2. Enlace publico de ngrok (si ngrok esta instalado)
REM   3. Abre la app en el navegador
REM  Uso: doble clic. Para apagar todo: cierra esta ventana y la de ngrok.
REM ==============================================================
title StockPot - servidor
cd /d "%~dp0backend"

if not exist ".venv\Scripts\waitress-serve.exe" (
    echo [ERROR] Falta el entorno virtual o Waitress. Ejecuta en backend:
    echo         python -m venv .venv  y luego  .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)
if not exist ".env" (
    echo [ERROR] Falta el archivo backend\.env. Copia .env.example como .env y llenalo.
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
    echo [ERROR] El puerto 5000 ya esta en uso: StockPot ya esta abierto en otra ventana
    echo         o hay otro servidor corriendo. Cierralo y vuelve a intentarlo.
    pause
    exit /b 1
)

echo ================================================================
echo  StockPot
echo   En este PC:  http://127.0.0.1:5000
echo   Para apagar todo: cierra esta ventana y la de ngrok.
echo ================================================================
echo.

REM --- ngrok: enlace publico (opcional) ---------------------------
where ngrok >nul 2>nul
if errorlevel 1 (
    echo [AVISO] ngrok no esta instalado: StockPot solo funcionara en este PC.
) else (
    set "DOMINIO="
    if exist "%~dp0ngrok-dominio.txt" set /p DOMINIO=<"%~dp0ngrok-dominio.txt"
    call :abrir_ngrok
    REM Cuando ngrok este listo, muestra el enlace publico aqui y lo copia al portapapeles
    start "" /b powershell -NoProfile -Command "Start-Sleep 6; try { $u = (Invoke-RestMethod http://127.0.0.1:4040/api/tunnels).tunnels | Where-Object proto -eq 'https' | Select-Object -First 1 -ExpandProperty public_url; Set-Clipboard $u; Write-Host ''; Write-Host ('  Enlace publico: ' + $u + '   (copiado al portapapeles)') -ForegroundColor Green; Write-Host '' } catch { Write-Host '  [AVISO] No se pudo leer el enlace de ngrok; miralo en su ventana.' -ForegroundColor Yellow }"
)

REM --- Abre la app en el navegador cuando el servidor este listo ----
start "" cmd /c "timeout /t 3 /nobreak >nul & start http://127.0.0.1:5000"

REM --- Servidor (queda corriendo en esta ventana) -------------------
".venv\Scripts\waitress-serve.exe" --host=127.0.0.1 --port=5000 --call app:create_app
pause
exit /b

:abrir_ngrok
if defined DOMINIO (
    start "StockPot - ngrok" ngrok http --url=%DOMINIO% 5000
) else (
    start "StockPot - ngrok" ngrok http 5000
)
exit /b
