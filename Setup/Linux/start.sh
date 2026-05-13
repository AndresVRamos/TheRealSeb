#!/bin/bash

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

# Obtener directorio raiz del proyecto
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Cambiar al directorio del proyecto
cd "$PROJECT_DIR"

# Verificar que .env existe
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo -e "${RED}[ERROR] No se encontro el archivo .env${NC}"
    echo "        Ejecuta ./Setup/Linux/install.sh primero para configurarlo."
    exit 1
fi

# Verificar que Python está disponible
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ERROR] Python3 no esta instalado.${NC}"
    echo "        Ejecuta ./Setup/Linux/install.sh para instalarlo."
    exit 1
fi

# Verificar que FFmpeg está disponible
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${RED}[ERROR] FFmpeg no esta instalado.${NC}"
    echo "        Ejecuta ./Setup/Linux/install.sh para instalarlo."
    exit 1
fi

# Iniciar el bot
echo "Iniciando The Real Seb..."
"$PROJECT_DIR/venv/bin/python3" "$PROJECT_DIR/maniac.py"

# Si llegamos aquí, el bot se detuvo
echo ""
echo "El bot se ha detenido."
