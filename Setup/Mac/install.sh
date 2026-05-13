#!/bin/bash

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Obtener directorio raiz del proyecto
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo ""
echo "============================================================"
echo "              THE REAL SEB - INSTALADOR (macOS)"
echo "============================================================"
echo ""

# ===== VERIFICAR/INSTALAR HOMEBREW =====
echo -e "[0/4] Verificando Homebrew..."

if ! command -v brew &> /dev/null; then
    echo -e "      ${YELLOW}Homebrew no encontrado. Instalando...${NC}"
    echo ""
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Agregar brew al PATH si es Apple Silicon
    if [[ -f "/opt/homebrew/bin/brew" ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi

    if ! command -v brew &> /dev/null; then
        echo -e "      ${RED}[ERROR] No se pudo instalar Homebrew.${NC}"
        echo "               Instalalo manualmente desde https://brew.sh"
        exit 1
    fi
    echo -e "      ${GREEN}Homebrew instalado correctamente.${NC}"
else
    echo -e "      ${GREEN}Homebrew encontrado.${NC}"
fi

# ===== VERIFICAR/INSTALAR PYTHON =====
echo ""
echo -e "[1/4] Verificando Python..."

if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo -e "      ${GREEN}Python $PYTHON_VERSION encontrado.${NC}"
else
    echo -e "      ${YELLOW}Python3 no encontrado. Instalando con Homebrew...${NC}"
    brew install python

    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        echo -e "      ${GREEN}Python $PYTHON_VERSION instalado correctamente.${NC}"
    else
        echo -e "      ${RED}[ERROR] No se pudo instalar Python3.${NC}"
        exit 1
    fi
fi

# ===== VERIFICAR/INSTALAR FFMPEG =====
echo ""
echo -e "[2/4] Verificando FFmpeg..."

if command -v ffmpeg &> /dev/null; then
    echo -e "      ${GREEN}FFmpeg encontrado.${NC}"
else
    echo -e "      ${YELLOW}FFmpeg no encontrado. Instalando con Homebrew...${NC}"
    brew install ffmpeg

    if command -v ffmpeg &> /dev/null; then
        echo -e "      ${GREEN}FFmpeg instalado correctamente.${NC}"
    else
        echo -e "      ${RED}[ERROR] No se pudo instalar FFmpeg.${NC}"
        exit 1
    fi
fi

# ===== INSTALAR DEPENDENCIAS PYTHON =====
echo ""
echo -e "[3/4] Instalando dependencias de Python..."
echo "      Esto puede tardar unos minutos..."
echo ""

cd "$PROJECT_DIR"
python3 -m pip install -r requirements.txt --quiet 2>/dev/null || pip3 install -r requirements.txt --quiet

if [ $? -ne 0 ]; then
    echo -e "      ${RED}[ERROR] Fallo al instalar dependencias.${NC}"
    echo "               Intenta ejecutar manualmente: pip3 install -r requirements.txt"
    exit 1
fi

echo -e "      ${GREEN}Dependencias instaladas correctamente.${NC}"

# ===== CONFIGURAR .ENV =====
echo ""
echo -e "[4/4] Configurando archivo .env..."

if [ -f "$PROJECT_DIR/.env" ]; then
    echo -e "      ${BLUE}Archivo .env ya existe. Saltando configuracion.${NC}"
    echo "      Si necesitas reconfigurarlo, edita el archivo .env manualmente."
else
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    echo "      Archivo .env creado desde .env.example"
    echo ""
    echo "============================================================"
    echo "                   CONFIGURACION REQUERIDA"
    echo "============================================================"
    echo ""
    echo "Necesitas configurar al menos el TOKEN de Discord:"
    echo ""
    echo "1. Ve a https://discord.com/developers/applications"
    echo "2. Crea una aplicacion o selecciona una existente"
    echo "3. Ve a \"Bot\" en el menu lateral"
    echo "4. Copia el TOKEN del bot"
    echo "5. Edita el archivo .env y reemplaza YOUR_DISCORD_BOT_TOKEN_HERE"
    echo ""
    echo "OPCIONAL (para soporte de Spotify):"
    echo "- Ve a https://developer.spotify.com/dashboard"
    echo "- Crea una app y copia Client ID y Client Secret"
    echo ""
    echo "OPCIONAL (para mejores letras):"
    echo "- Ve a https://genius.com/api-clients"
    echo "- Crea una app y copia el Access Token"
    echo ""

    read -p "Deseas abrir el archivo .env ahora? (s/n): " OPEN_ENV
    if [[ "$OPEN_ENV" =~ ^[Ss]$ ]]; then
        # Usar el editor por defecto de macOS
        open -e "$PROJECT_DIR/.env" 2>/dev/null || nano "$PROJECT_DIR/.env"
    fi
fi

# ===== RESUMEN FINAL =====
echo ""
echo "============================================================"
echo -e "           ${GREEN}INSTALACION COMPLETADA${NC}"
echo "============================================================"
echo ""

# ===== OPCIONES POST-INSTALACION =====
echo "Que deseas hacer ahora?"
echo ""
echo "  1) Iniciar el bot"
echo "  2) Agregar al inicio del sistema"
echo "  3) Ambos (agregar al inicio e iniciar)"
echo "  4) Nada, salir"
echo ""
read -p "Opcion (1/2/3/4): " POST_OPTION

case $POST_OPTION in
    1)
        echo ""
        echo "Iniciando el bot..."
        exec "$SCRIPT_DIR/start.sh"
        ;;
    2)
        echo ""
        "$SCRIPT_DIR/add-to-startup.sh"
        ;;
    3)
        echo ""
        "$SCRIPT_DIR/add-to-startup.sh"
        echo ""
        echo "Iniciando el bot..."
        exec "$SCRIPT_DIR/start.sh"
        ;;
    *)
        echo ""
        echo "Recuerda configurar el archivo .env antes de iniciar el bot."
        echo ""
        ;;
esac
