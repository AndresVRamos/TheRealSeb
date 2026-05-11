@echo off
title The Real Seb - Remover del Inicio

echo.
echo ============================================================
echo          THE REAL SEB - REMOVER DEL INICIO
echo ============================================================
echo.

set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_NAME=The Real Seb.lnk"

if not exist "%STARTUP_FOLDER%\%SHORTCUT_NAME%" (
    echo [INFO] No hay acceso directo de The Real Seb en el inicio.
    echo.
    pause
    exit /b 0
)

set /p CONFIRM="Deseas remover The Real Seb del inicio de Windows? (S/N): "
if /i not "%CONFIRM%"=="S" (
    echo Operacion cancelada.
    pause
    exit /b 0
)

del "%STARTUP_FOLDER%\%SHORTCUT_NAME%"

if %errorlevel% equ 0 (
    echo.
    echo [OK] The Real Seb removido del inicio de Windows.
    echo.
) else (
    echo [ERROR] No se pudo eliminar el acceso directo.
)

pause
