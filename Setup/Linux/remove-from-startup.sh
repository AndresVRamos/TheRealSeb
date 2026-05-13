#!/bin/bash

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "============================================================"
echo "          THE REAL SEB - REMOVER DEL INICIO"
echo "============================================================"
echo ""

AUTOSTART_DIR="$HOME/.config/autostart"
DESKTOP_FILE="$AUTOSTART_DIR/the-real-seb.desktop"
SYSTEMD_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SYSTEMD_DIR/the-real-seb.service"

# Verificar qué existe
DESKTOP_EXISTS=false
SYSTEMD_EXISTS=false

if [ -f "$DESKTOP_FILE" ]; then
    DESKTOP_EXISTS=true
fi

if [ -f "$SERVICE_FILE" ]; then
    SYSTEMD_EXISTS=true
fi

# Si no existe ninguno
if [ "$DESKTOP_EXISTS" = false ] && [ "$SYSTEMD_EXISTS" = false ]; then
    echo -e "${YELLOW}[INFO] No hay configuracion de autostart de The Real Seb.${NC}"
    echo ""
    exit 0
fi

# Mostrar lo que se encontró
echo "Se encontraron las siguientes configuraciones:"
echo ""

if [ "$DESKTOP_EXISTS" = true ]; then
    echo "  1) Autostart de escritorio: $DESKTOP_FILE"
fi

if [ "$SYSTEMD_EXISTS" = true ]; then
    echo "  2) Servicio systemd: $SERVICE_FILE"
fi

echo ""

# Si existen ambos
if [ "$DESKTOP_EXISTS" = true ] && [ "$SYSTEMD_EXISTS" = true ]; then
    echo "Que deseas remover?"
    echo "  1) Solo autostart de escritorio"
    echo "  2) Solo servicio systemd"
    echo "  3) Ambos"
    echo ""
    read -p "Opcion (1/2/3): " OPTION

    case $OPTION in
        1)
            SYSTEMD_EXISTS=false
            ;;
        2)
            DESKTOP_EXISTS=false
            ;;
        3)
            # Mantener ambos true
            ;;
        *)
            echo -e "${RED}Opcion no valida.${NC}"
            exit 1
            ;;
    esac
else
    read -p "Deseas remover esta configuracion? (s/n): " CONFIRM
    if [[ ! "$CONFIRM" =~ ^[Ss]$ ]]; then
        echo "Operacion cancelada."
        exit 0
    fi
fi

# Remover autostart de escritorio
if [ "$DESKTOP_EXISTS" = true ]; then
    rm -f "$DESKTOP_FILE"
    echo -e "${GREEN}[OK] Autostart de escritorio removido.${NC}"
fi

# Remover servicio systemd
if [ "$SYSTEMD_EXISTS" = true ]; then
    systemctl --user stop the-real-seb.service 2>/dev/null
    systemctl --user disable the-real-seb.service 2>/dev/null
    rm -f "$SERVICE_FILE"
    systemctl --user daemon-reload
    echo -e "${GREEN}[OK] Servicio systemd removido.${NC}"
fi

echo ""
echo "The Real Seb ya no iniciara automaticamente."
echo ""
