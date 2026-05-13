#!/bin/bash

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo "============================================================"
echo "           THE REAL SEB - AGREGAR AL INICIO (macOS)"
echo "============================================================"
echo ""

# Obtener rutas
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_NAME="com.therealseb.bot.plist"
PLIST_PATH="$LAUNCH_AGENTS_DIR/$PLIST_NAME"

# Crear directorio LaunchAgents si no existe
mkdir -p "$LAUNCH_AGENTS_DIR"

# Verificar si ya existe
if [ -f "$PLIST_PATH" ]; then
    echo -e "${BLUE}[INFO] Ya existe un Launch Agent configurado.${NC}"
    echo ""
    read -p "Deseas reemplazarlo? (s/n): " OVERWRITE
    if [[ ! "$OVERWRITE" =~ ^[Ss]$ ]]; then
        echo "Operacion cancelada."
        exit 0
    fi
    # Descargar el agente actual antes de reemplazar
    launchctl unload "$PLIST_PATH" 2>/dev/null
    rm "$PLIST_PATH"
fi

# Obtener la ruta de Python
PYTHON_PATH=$(which python3)

# Crear el archivo plist
echo "Creando Launch Agent..."

cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.therealseb.bot</string>

    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_PATH</string>
        <string>$PROJECT_DIR/maniac.py</string>
    </array>

    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <false/>

    <key>StandardOutPath</key>
    <string>$PROJECT_DIR/data/bot.log</string>

    <key>StandardErrorPath</key>
    <string>$PROJECT_DIR/data/bot_error.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
    </dict>
</dict>
</plist>
EOF

if [ $? -ne 0 ]; then
    echo -e "${RED}[ERROR] No se pudo crear el Launch Agent.${NC}"
    exit 1
fi

# Cargar el Launch Agent
launchctl load "$PLIST_PATH"

echo ""
echo -e "${GREEN}[OK] Launch Agent creado exitosamente.${NC}"
echo ""
echo "El bot se iniciara automaticamente cuando inicies sesion en macOS."
echo ""
echo "Ubicacion: $PLIST_PATH"
echo ""
echo "Para removerlo, ejecuta ./Setup/Mac/remove-from-startup.sh"
echo ""
