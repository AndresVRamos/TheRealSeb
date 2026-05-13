#!/bin/bash

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' 

# Obtener directorio raíz del proyecto (Ajustado para ser más robusto)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo ""
echo "============================================================"
echo "          THE REAL SEB - INSTALADOR INQUEBRANTABLE"
echo "============================================================"
echo ""

# Detectar el gestor de paquetes
detect_package_manager() {
    if command -v apt-get &> /dev/null; then
        PKG_MANAGER="apt"
        PKG_INSTALL="sudo apt-get install -y"
        PKG_UPDATE="sudo apt-get update"
    elif command -v dnf &> /dev/null; then
        PKG_MANAGER="dnf"
        PKG_INSTALL="sudo dnf install -y"
        PKG_UPDATE="sudo dnf check-update"
    elif command -v pacman &> /dev/null; then
        PKG_MANAGER="pacman"
        PKG_INSTALL="sudo pacman -S --noconfirm"
        PKG_UPDATE="sudo pacman -Sy"
    else
        PKG_MANAGER="unknown"
    fi
}

detect_package_manager

# ===== VERIFICAR/INSTALAR PYTHON Y VENV =====
echo -e "[1/4] Verificando Python y Entorno Virtual..."

if [ "$PKG_MANAGER" = "apt" ]; then
    $PKG_UPDATE
    # python3-venv es vital en Ubuntu moderno
    $PKG_INSTALL python3 python3-pip python3-venv python3-full
fi

# ===== VERIFICAR/INSTALAR FFMPEG =====
echo ""
echo -e "[2/4] Verificando FFmpeg (necesario para audio)..."

if command -v ffmpeg &> /dev/null; then
    echo -e "      ${GREEN}FFmpeg encontrado.${NC}"
else
    echo -e "      ${YELLOW}Instalando FFmpeg...${NC}"
    $PKG_INSTALL ffmpeg
fi

# ===== CREAR ENTORNO VIRTUAL E INSTALAR DEPENDENCIAS =====
echo ""
echo -e "[3/4] Configurando entorno virtual y dependencias..."
cd "$PROJECT_DIR"

if [ -d "$SCRIPT_DIR/venv" ]; then
    echo "      Eliminando venv mal ubicado en Setup/Linux..."
    rm -rf "$SCRIPT_DIR/venv"
fi

# Crear venv si no existe
if [ ! -d "venv" ]; then
    echo "      Creando entorno virtual (venv)..."
    python3 -m venv venv
fi

# Instalar dependencias dentro del venv
echo "      Instalando paquetes en venv (esto evita errores de sistema)..."
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt --quiet

if [ $? -eq 0 ]; then
    echo -e "      ${GREEN}Dependencias instaladas correctamente en venv.${NC}"
else
    echo -e "      ${RED}[ERROR] Falló la instalación de dependencias.${NC}"
    exit 1
fi

# ===== CONFIGURAR .ENV =====
echo ""
echo -e "[4/4] Configurando archivo .env..."

if [ -f "$PROJECT_DIR/.env" ]; then
    echo -e "      ${BLUE}Archivo .env ya existe.${NC}"
else
    if [ -f "$PROJECT_DIR/.env.example" ]; then
        cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
        echo "      Archivo .env creado desde .env.example"
    else
        echo "TOKEN=TU_TOKEN_AQUI" > "$PROJECT_DIR/.env"
        echo "      Archivo .env nuevo creado."
    fi
    
    echo -e "${YELLOW}Recuerda poner tu Token de Discord en el archivo .env${NC}"
fi

# Asegurar permisos de ejecución para otros scripts
chmod +x "$SCRIPT_DIR"/*.sh 2>/dev/null || true

echo ""
echo "============================================================"
echo -e "           ${GREEN}INSTALACIÓN COMPLETADA${NC}"
echo "============================================================"
echo ""
echo "Para encender el bot manualmente usa: ./venv/bin/python main.py"
echo ""

# ===== OPCIÓN DE INICIO =====
read -p "¿Deseas intentar iniciar el bot ahora? (s/n): " START_NOW
if [[ "$START_NOW" =~ ^[Ss]$ ]]; then
    if [ -f "main.py" ]; then
        ./venv/bin/python3 main.py
    else
        echo -e "${RED}No se encontró main.py en $PROJECT_DIR${NC}"
    fi
fi
