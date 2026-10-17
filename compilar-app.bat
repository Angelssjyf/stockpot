@echo off
REM ==============================================================
REM  StockPot - Compila la app Flutter para web (mobile\build\web).
REM  Ejecutalo cada vez que cambie el codigo de la app (carpeta mobile).
REM ==============================================================
title StockPot - compilando app
cd /d "%~dp0mobile"

echo Compilando la app web de StockPot (tarda alrededor de 1 minuto)...
call flutter build web --release --no-wasm-dry-run
if errorlevel 1 (
    echo.
    echo [ERROR] No se pudo compilar. Revisa los mensajes de arriba.
    pause
    exit /b 1
)

echo.
echo Listo. Ahora abre  iniciar.bat  para usar la app.
pause
