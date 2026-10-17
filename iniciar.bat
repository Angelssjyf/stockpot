@echo off
REM ==============================================================
REM  StockPot - Inicia el servidor y abre la app en el navegador.
REM  Uso: doble clic en este archivo. Para detener: cierra la ventana.
REM ==============================================================
title StockPot - servidor
cd /d "%~dp0backend"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] No existe el entorno virtual. Sigue los pasos de instalacion del README.
    pause
    exit /b 1
)
if not exist ".env" (
    echo [ERROR] Falta el archivo backend\.env. Copia .env.example como .env y llenalo.
    pause
    exit /b 1
)
if not exist "..\mobile\build\web\index.html" (
    echo [AVISO] La app web no esta compilada: ejecuta  compilar-app.bat  primero.
    echo.
)

echo Iniciando StockPot en http://127.0.0.1:5000 ...
echo Para detener el servidor, cierra esta ventana.
echo.

REM Abre el navegador 3 segundos despues, cuando el servidor ya esta listo
start "" cmd /c "timeout /t 3 /nobreak >nul & start http://127.0.0.1:5000"

".venv\Scripts\python.exe" run.py
pause
