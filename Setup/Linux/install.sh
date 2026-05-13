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
echo "              THE REAL SEB - INSTALADOR (Linux)"
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
    elif command -v yum &> /dev/null; then
        PKG_MANAGER="yum"
        PKG_INSTALL="sudo yum install -y"
        PKG_UPDATE="sudo yum check-update"
    elif command -v pacman &> /dev/null; then
        PKG_MANAGER="pacman"
        PKG_INSTALL="sudo pacman -S --noconfirm"
        PKG_UPDATE="sudo pacman -Sy"
    elif command -v zypper &> /dev/null; then
        PKG_MANAGER="zypper"
        PKG_INSTALL="sudo zypper install -y"
        PKG_UPDATE="sudo zypper refresh"
    else
        PKG_MANAGER="unknown"
    fi
}

detect_package_manager

# ===== VERIFICAR/INSTALAR PYTHON =====
echo -e "[1/4] Verificando Python..."

if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo -e "      ${GREEN}Python $PYTHON_VERSION encontrado.${NC}"
else
    echo -e "      ${YELLOW}Python3 no encontrado. Intentando instalar...${NC}"

    if [ "$PKG_MANAGER" = "unknown" ]; then
        echo -e "      ${RED}[ERROR] No se pudo detectar el gestor de paquetes.${NC}"
        echo "               Instala Python3 manualmente y ejecuta este script de nuevo."
        exit 1
    fi

    echo "      Actualizando repositorios..."
    $PKG_UPDATE

    echo "      Instalando Python3..."
    case $PKG_MANAGER in
        apt)
            $PKG_INSTALL python3 python3-pip python3-venv
            ;;
        dnf|yum)
            $PKG_INSTALL python3 python3-pip
            ;;
        pacman)
            $PKG_INSTALL python python-pip
            ;;
        zypper)
            $PKG_INSTALL python3 python3-pip
            ;;
    esac

    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        echo -e "      ${GREEN}Python $PYTHON_VERSION instalado correctamente.${NC}"
    else
        echo -e "      ${RED}[ERROR] No se pudo instalar Python3.${NC}"
        echo "               Instalalo manualmente y ejecuta este script de nuevo."
        exit 1
    fi
fi

# ===== VERIFICAR/INSTALAR FFMPEG =====
echo ""
echo -e "[2/4] Verificando FFmpeg..."

if command -v ffmpeg &> /dev/null; then
    echo -e "      ${GREEN}FFmpeg encontrado.${NC}"
else
    echo -e "      ${YELLOW}FFmpeg no encontrado. Intentando instalar...${NC}"

    if [ "$PKG_MANAGER" = "unknown" ]; then
        echo -e "      ${RED}[ERROR] No se pudo detectar el gestor de paquetes.${NC}"
        echo "               Instala FFmpeg manualmente y ejecuta este script de nuevo."
        exit 1
    fi

    echo "      Instalando FFmpeg..."
    case $PKG_MANAGER in
        apt)
            $PKG_INSTALL ffmpeg
            ;;
        dnf|yum)
            # Fedora/RHEL necesita RPM Fusion para ffmpeg
            if [ "$PKG_MANAGER" = "dnf" ]; then
                echo "      Nota: FFmpeg puede requerir RPM Fusion en Fedora/RHEL"
                sudo dnf install -y https://download1.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm 2>/dev/null || true
            fi
            $PKG_INSTALL ffmpeg
            ;;
        pacman)
            $PKG_INSTALL ffmpeg
            ;;
        zypper)
            $PKG_INSTALL ffmpeg
            ;;
    esac

    if command -v ffmpeg &> /dev/null; then
        echo -e "      ${GREEN}FFmpeg instalado correctamente.${NC}"
    else
        echo -e "      ${RED}[ERROR] No se pudo instalar FFmpeg.${NC}"
        echo "               Instalalo manualmente y ejecuta este script de nuevo."
        echo ""
        echo "         Debian/Ubuntu: sudo apt install ffmpeg"
        echo "         Fedora:        sudo dnf install ffmpeg"
        echo "         Arch:          sudo pacman -S ffmpeg"
        exit 1
    fi
fi

# ===== INSTALAR DEPENDENCIAS PYTHON =====
echo ""
echo -e "[3/4] Instalando dependencias de Python..."
echo "      Esto puede tardar unos minutos..."
echo ""

# Verificar si pip está disponible
if ! command -v pip3 &> /dev/null && ! python3 -m pip --version &> /dev/null; then
    echo -e "      ${YELLOW}pip no encontrado. Intentando instalar...${NC}"
    case $PKG_MANAGER in
        apt)
            $PKG_INSTALL python3-pip
            ;;
        dnf|yum)
            $PKG_INSTALL python3-pip
            ;;
        pacman)
            $PKG_INSTALL python-pip
            ;;
        zypper)
            $PKG_INSTALL python3-pip
            ;;
    esac
fi

# Instalar dependencias
cd "$PROJECT_DIR"
python3 -m pip install -r requirements.txt --quiet --user 2>/dev/null || pip3 install -r requirements.txt --quiet --user

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
        # Intentar abrir con el editor disponible
        if command -v nano &> /dev/null; then
            nano "$PROJECT_DIR/.env"
        elif command -v vim &> /dev/null; then
            vim "$PROJECT_DIR/.env"
        elif command -v vi &> /dev/null; then
            vi "$PROJECT_DIR/.env"
        else
            echo "No se encontro un editor de texto. Edita .env manualmente."
        fi
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
