@echo off
title The Real Seb - Instalador

echo.
echo ============================================================
echo              THE REAL SEB - INSTALADOR
echo ============================================================
echo.

:: ===== VERIFICAR PYTHON =====
echo [1/4] Verificando Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no esta instalado o no esta en el PATH.
    echo.
    echo         Descarga Python desde: https://www.python.org/downloads/
    echo         IMPORTANTE: Marca "Add Python to PATH" durante la instalacion.
    echo.
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo         Python %PYTHON_VERSION% encontrado.

:: ===== VERIFICAR FFmpeg =====
echo.
echo [2/4] Verificando FFmpeg...
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] FFmpeg no esta instalado o no esta en el PATH.
    echo.
    echo         FFmpeg es NECESARIO para reproducir audio.
    echo.
    echo         Opciones de instalacion:
    echo         1. Usando winget ^(recomendado^):
    echo            winget install ffmpeg
    echo.
    echo         2. Manual:
    echo            - Descarga desde: https://ffmpeg.org/download.html
    echo            - Extrae y agrega la carpeta 'bin' al PATH del sistema
    echo.
    echo         Despues de instalar FFmpeg, ejecuta este instalador de nuevo.
    echo.
    pause
    exit /b 1
)
echo         FFmpeg encontrado.

:: ===== INSTALAR DEPENDENCIAS =====
echo.
echo [3/4] Instalando dependencias de Python...
echo         Esto puede tardar unos minutos...
echo.
pip install -r requirements.txt --quiet
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

if exist .env (
    echo         Archivo .env ya existe. Saltando configuracion.
    echo         Si necesitas reconfigurarlo, edita el archivo .env manualmente.
) else (
    copy .env.example .env >nul
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
        notepad .env
    )
)

:: ===== RESUMEN FINAL =====
echo.
echo ============================================================
echo                   INSTALACION COMPLETADA
echo ============================================================
echo.
echo Para iniciar el bot:
echo   - Doble clic en start.bat
echo   - O ejecuta: python main.pyw
echo.
echo Para que inicie con Windows:
echo   - Ejecuta add-to-startup.bat
echo.
echo Recuerda configurar el archivo .env antes de iniciar el bot.
echo.
pause
