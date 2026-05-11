@echo off
title The Real Seb

:: Cambiar al directorio del script
cd /d "%~dp0"

:: Verificar que .env existe
if not exist .env (
    echo [ERROR] No se encontro el archivo .env
    echo         Ejecuta install.bat primero para configurarlo.
    pause
    exit /b 1
)

:: Iniciar el bot
echo Iniciando The Real Seb...
start "" pythonw main.pyw

echo.
echo [OK] Bot iniciado correctamente.
echo     Esta ventana se cerrara en 5 segundos...
timeout /t 5 /nobreak >nul
