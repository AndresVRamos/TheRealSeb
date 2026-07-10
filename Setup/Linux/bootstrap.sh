#!/bin/bash
# ============================================================
#   THE REAL SEB - Bootstrap para Linux
#   Descarga e instala el bot sin necesidad de git
#
#   Uso:
#     curl -sSL https://raw.githubusercontent.com/AndresVRamos/TheRealSeb/main/Setup/Linux/bootstrap.sh | bash
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

REPO="AndresVRamos/TheRealSeb"
BRANCH="main"
INSTALL_DIR="$HOME/TheRealSeb"
ZIP_URL="https://github.com/$REPO/archive/refs/heads/$BRANCH.zip"
TEMP_ZIP="/tmp/therealse_download.zip"
TEMP_DIR="/tmp/therealse_extract"

echo ""
echo "============================================================"
echo "          THE REAL SEB - Bootstrap (Linux)"
echo "============================================================"
echo ""

# Verificar herramientas necesarias para el bootstrap
for tool in curl unzip; do
    if ! command -v "$tool" &>/dev/null; then
        echo -e "${YELLOW}Instalando $tool...${NC}"
        if command -v apt-get &>/dev/null; then
            sudo apt-get install -y "$tool"
        elif command -v dnf &>/dev/null; then
            sudo dnf install -y "$tool"
        elif command -v pacman &>/dev/null; then
            sudo pacman -S --noconfirm "$tool"
        else
            echo -e "${RED}[ERROR] No se pudo instalar $tool. Instálalo manualmente.${NC}"
            exit 1
        fi
    fi
done

# Descargar el repositorio como ZIP
echo "Descargando The Real Seb desde GitHub..."
curl -L --progress-bar "$ZIP_URL" -o "$TEMP_ZIP"
echo -e "${GREEN}Descarga completada.${NC}"

# Extraer
echo "Extrayendo archivos..."
rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"
unzip -q "$TEMP_ZIP" -d "$TEMP_DIR"
rm "$TEMP_ZIP"

# Mover al directorio de instalación
EXTRACTED="$TEMP_DIR/TheRealSeb-$BRANCH"
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}El directorio $INSTALL_DIR ya existe. Actualizando archivos...${NC}"
    # Preservar .env existente
    if [ -f "$INSTALL_DIR/.env" ]; then
        cp "$INSTALL_DIR/.env" "$TEMP_DIR/.env.backup"
    fi
fi

cp -r "$EXTRACTED/." "$INSTALL_DIR/"

# Restaurar .env si existía
if [ -f "$TEMP_DIR/.env.backup" ]; then
    mv "$TEMP_DIR/.env.backup" "$INSTALL_DIR/.env"
    echo -e "${GREEN}Configuración .env existente preservada.${NC}"
fi

rm -rf "$TEMP_DIR"

echo -e "${GREEN}Archivos instalados en: $INSTALL_DIR${NC}"
echo ""

# Ejecutar el instalador real
chmod +x "$INSTALL_DIR/Setup/Linux/install.sh"
cd "$INSTALL_DIR"
exec ./Setup/Linux/install.sh
