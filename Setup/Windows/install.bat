@echo off
title The Real Seb - Instalador

:: Cambiar al directorio raiz del proyecto
cd /d "%~dp0..\.."
set "PROJECT_DIR=%cd%"

echo.
echo ============================================================
echo              THE REAL SEB - INSTALADOR
echo ============================================================
echo.

:: ===== VERIFICAR/INSTALAR PYTHON =====
echo [1/4] Verificando Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo         Python no encontrado. Intentando instalar con winget...
    echo.
    winget --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] winget no esta disponible para instalar Python automaticamente.
        echo.
        echo         Opciones:
        echo         1. Instala winget desde Microsoft Store ^(App Installer^)
        echo         2. Descarga Python manualmente: https://www.python.org/downloads/
        echo            IMPORTANTE: Marca "Add Python to PATH" durante la instalacion.
        echo.
        pause
        exit /b 1
    )
    echo         Instalando Python 3.12 con winget...
    echo         ^(Esto puede tardar unos minutos^)
    echo.
    winget install Python.Python.3.12 --accept-source-agreements --accept-package-agreements
    if %errorlevel% neq 0 (
        echo [ERROR] Fallo la instalacion de Python.
        echo         Descarga Python manualmente: https://www.python.org/downloads/
        pause
        exit /b 1
    )
    echo.
    echo [IMPORTANTE] Python se instalo correctamente.
    echo              DEBES CERRAR esta ventana y ejecutar install.bat de nuevo
    echo              para que el PATH se actualice.
    echo.
    pause
    exit /b 0
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo         Python %PYTHON_VERSION% encontrado.

:: ===== VERIFICAR/INSTALAR FFmpeg =====
echo.
echo [2/4] Verificando FFmpeg...
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo         FFmpeg no encontrado. Intentando instalar con winget...
    echo.
    winget --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] winget no esta disponible para instalar FFmpeg automaticamente.
        echo.
        echo         Opciones:
        echo         1. Instala winget desde Microsoft Store ^(App Installer^)
        echo         2. Descarga FFmpeg manualmente: https://ffmpeg.org/download.html
        echo            - Extrae y agrega la carpeta 'bin' al PATH del sistema
        echo.
        pause
        exit /b 1
    )
    echo         Instalando FFmpeg con winget...
    echo         ^(Esto puede tardar unos minutos^)
    echo.
    winget install Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
    if %errorlevel% neq 0 (
        echo [ERROR] Fallo la instalacion de FFmpeg.
        echo         Descarga FFmpeg manualmente: https://ffmpeg.org/download.html
        pause
        exit /b 1
    )
    echo.
    echo [IMPORTANTE] FFmpeg se instalo correctamente.
    echo              DEBES CERRAR esta ventana y ejecutar install.bat de nuevo
    echo              para que el PATH se actualice.
    echo.
    pause
    exit /b 0
)
echo         FFmpeg encontrado.

:: ===== INSTALAR DEPENDENCIAS =====
echo.
echo [3/4] Instalando dependencias de Python...
echo         Esto puede tardar unos minutos...
echo.
pip install -r "%PROJECT_DIR%\requirements.txt" --quiet
if %errorlevel% neq 0 (
    echo [ERROR] Fallo al instalar dependencias.
    echo         Intenta ejecutar manualmente: pip install -r requirements.txt
    pause
    exit /b 1
)
echo         Dependencias instaladas correctamente.

:: ===== CONFIGURAR .ENV =====
echo.
echo [4/4] Configurando archivo .env...

if exist "%PROJECT_DIR%\.env" (
    echo         Archivo .env ya existe. Saltando configuracion.
    echo         Si necesitas reconfigurarlo, edita el archivo .env manualmente.
) else (
    copy "%PROJECT_DIR%\.env.example" "%PROJECT_DIR%\.env" >nul
    echo         Archivo .env creado desde .env.example
    echo.
    echo ============================================================
    echo                   CONFIGURACION REQUERIDA
    echo ============================================================
    echo.
    echo Necesitas configurar al menos el TOKEN de Discord:
    echo.
    echo 1. Ve a https://discord.com/developers/applications
    echo 2. Crea una aplicacion o selecciona una existente
    echo 3. Ve a "Bot" en el menu lateral
    echo 4. Copia el TOKEN del bot
    echo 5. Edita el archivo .env y reemplaza YOUR_DISCORD_BOT_TOKEN_HERE
    echo.
    echo OPCIONAL ^(para soporte de Spotify^):
    echo - Ve a https://developer.spotify.com/dashboard
    echo - Crea una app y copia Client ID y Client Secret
    echo.
    echo OPCIONAL ^(para mejores letras^):
    echo - Ve a https://genius.com/api-clients
    echo - Crea una app y copia el Access Token
    echo.

    set /p OPEN_ENV="Deseas abrir el archivo .env ahora? (S/N): "
    if /i "%OPEN_ENV%"=="S" (
        notepad "%PROJECT_DIR%\.env"
    )
)

:: ===== RESUMEN FINAL =====
echo.
echo ============================================================
echo                   INSTALACION COMPLETADA
echo ============================================================
echo.

:: ===== OPCIONES POST-INSTALACION =====
echo Que deseas hacer ahora?
echo.
echo   1) Iniciar el bot
echo   2) Agregar al inicio de Windows
echo   3) Ambos ^(agregar al inicio e iniciar^)
echo   4) Nada, salir
echo.
set /p POST_OPTION="Opcion (1/2/3/4): "

if "%POST_OPTION%"=="1" (
    echo.
    echo Iniciando el bot...
    call "%~dp0start.bat"
) else if "%POST_OPTION%"=="2" (
    echo.
    call "%~dp0add-to-startup.bat"
) else if "%POST_OPTION%"=="3" (
    echo.
    call "%~dp0add-to-startup.bat"
    echo.
    echo Iniciando el bot...
    call "%~dp0start.bat"
) else (
    echo.
    echo Recuerda configurar el archivo .env antes de iniciar el bot.
    echo.
    pause
)
