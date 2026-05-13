@echo off
title The Real Seb

:: Cambiar al directorio raiz del proyecto
cd /d "%~dp0..\.."
set "PROJECT_DIR=%cd%"

:: Verificar que .env existe
if not exist "%PROJECT_DIR%\.env" (
    echo [ERROR] No se encontro el archivo .env
    echo         Ejecuta Setup\Windows\install.bat primero para configurarlo.
    pause
    exit /b 1
)

:: Iniciar el bot
echo Iniciando The Real Seb...
start "" pythonw "%PROJECT_DIR%\main.pyw"

echo.
echo [OK] Bot iniciado correctamente.
echo     Esta ventana se cerrara en 5 segundos...
timeout /t 5 /nobreak >nul
