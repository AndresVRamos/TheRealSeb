@echo off
title The Real Seb - Agregar al Inicio

echo.
echo ============================================================
echo           THE REAL SEB - AGREGAR AL INICIO
echo ============================================================
echo.

:: Obtener la ruta actual del script
set "BOT_PATH=%~dp0"
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_NAME=The Real Seb.lnk"

:: Verificar si ya existe
if exist "%STARTUP_FOLDER%\%SHORTCUT_NAME%" (
    echo [INFO] Ya existe un acceso directo en el inicio.
    echo.
    set /p OVERWRITE="Deseas reemplazarlo? (S/N): "
    if /i not "%OVERWRITE%"=="S" (
        echo Operacion cancelada.
        pause
        exit /b 0
    )
    del "%STARTUP_FOLDER%\%SHORTCUT_NAME%"
)

:: Crear acceso directo usando PowerShell
echo Creando acceso directo en la carpeta de inicio...
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%STARTUP_FOLDER%\%SHORTCUT_NAME%'); $s.TargetPath = '%BOT_PATH%start.bat'; $s.WorkingDirectory = '%BOT_PATH%'; $s.WindowStyle = 7; $s.Description = 'The Real Seb Discord Bot'; $s.Save()"

if %errorlevel% neq 0 (
    echo [ERROR] No se pudo crear el acceso directo.
    pause
    exit /b 1
)

echo.
echo [OK] Acceso directo creado exitosamente.
echo.
echo El bot se iniciara automaticamente cuando enciendas Windows.
echo.
echo Ubicacion: %STARTUP_FOLDER%\%SHORTCUT_NAME%
echo.
echo Para removerlo, ejecuta remove-from-startup.bat
echo.
pause
