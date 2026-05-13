#!/bin/bash

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo "============================================================"
echo "          THE REAL SEB - REMOVER DEL INICIO (macOS)"
echo "============================================================"
echo ""

LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_NAME="com.therealseb.bot.plist"
PLIST_PATH="$LAUNCH_AGENTS_DIR/$PLIST_NAME"

if [ ! -f "$PLIST_PATH" ]; then
    echo -e "${BLUE}[INFO] No hay Launch Agent de The Real Seb configurado.${NC}"
    echo ""
    exit 0
fi

read -p "Deseas remover The Real Seb del inicio de macOS? (s/n): " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Ss]$ ]]; then
    echo "Operacion cancelada."
    exit 0
fi

# Descargar el Launch Agent
launchctl unload "$PLIST_PATH" 2>/dev/null

# Eliminar el archivo plist
rm "$PLIST_PATH"

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}[OK] The Real Seb removido del inicio de macOS.${NC}"
    echo ""
else
    echo -e "${RED}[ERROR] No se pudo eliminar el Launch Agent.${NC}"
fi
