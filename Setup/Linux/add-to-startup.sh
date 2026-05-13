#!/bin/bash

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo "============================================================"
echo "           THE REAL SEB - AGREGAR AL INICIO"
echo "============================================================"
echo ""

# Obtener directorios
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
AUTOSTART_DIR="$HOME/.config/autostart"
DESKTOP_FILE="$AUTOSTART_DIR/the-real-seb.desktop"
SYSTEMD_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SYSTEMD_DIR/the-real-seb.service"

# Preguntar qué método usar
echo "Selecciona el metodo de inicio automatico:"
echo ""
echo "  1) Autostart de escritorio (GNOME, KDE, XFCE, etc.)"
echo "     - Inicia cuando inicias sesion en el escritorio"
echo "     - Recomendado para uso con entorno grafico"
echo ""
echo "  2) Servicio systemd (usuario)"
echo "     - Inicia automaticamente sin necesidad de login grafico"
echo "     - Recomendado para servidores o uso headless"
echo ""
read -p "Opcion (1/2): " OPTION

case $OPTION in
    1)
        # ===== METODO AUTOSTART DESKTOP =====
        echo ""
        echo "Configurando autostart de escritorio..."

        # Crear directorio si no existe
        mkdir -p "$AUTOSTART_DIR"

        # Verificar si ya existe
        if [ -f "$DESKTOP_FILE" ]; then
            echo -e "${YELLOW}[INFO] Ya existe una entrada de autostart.${NC}"
            read -p "Deseas reemplazarla? (s/n): " OVERWRITE
            if [[ ! "$OVERWRITE" =~ ^[Ss]$ ]]; then
                echo "Operacion cancelada."
                exit 0
            fi
        fi

        # Crear archivo .desktop
        cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Type=Application
Name=The Real Seb
Comment=Discord Music Bot
Exec=bash -c 'cd "$PROJECT_DIR" && "$SCRIPT_DIR/start.sh"'
Path=$PROJECT_DIR
Terminal=false
Hidden=false
X-GNOME-Autostart-enabled=true
StartupNotify=false
EOF

        chmod +x "$DESKTOP_FILE"

        echo ""
        echo -e "${GREEN}[OK] Autostart configurado exitosamente.${NC}"
        echo ""
        echo "El bot se iniciara automaticamente cuando inicies sesion."
        echo ""
        echo -e "Ubicacion: ${BLUE}$DESKTOP_FILE${NC}"
        echo ""
        echo "Para removerlo, ejecuta ./Setup/Linux/remove-from-startup.sh"
        ;;

    2)
        # ===== METODO SYSTEMD USER SERVICE =====
        echo ""
        echo "Configurando servicio systemd..."

        # Crear directorio si no existe
        mkdir -p "$SYSTEMD_DIR"

        # Verificar si ya existe
        if [ -f "$SERVICE_FILE" ]; then
            echo -e "${YELLOW}[INFO] Ya existe un servicio systemd.${NC}"
            read -p "Deseas reemplazarlo? (s/n): " OVERWRITE
            if [[ ! "$OVERWRITE" =~ ^[Ss]$ ]]; then
                echo "Operacion cancelada."
                exit 0
            fi
            systemctl --user stop the-real-seb.service 2>/dev/null
            systemctl --user disable the-real-seb.service 2>/dev/null
        fi

        # Crear archivo de servicio
        cat > "$SERVICE_FILE" << EOF
[Unit]
Description=The Real Seb - Discord Music Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
ExecStart=/usr/bin/python3 $PROJECT_DIR/maniac.py
Restart=on-failure
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
EOF

        # Recargar systemd y habilitar servicio
        systemctl --user daemon-reload
        systemctl --user enable the-real-seb.service

        echo ""
        echo -e "${GREEN}[OK] Servicio systemd configurado exitosamente.${NC}"
        echo ""
        echo "Comandos utiles:"
        echo "  - Iniciar ahora:    systemctl --user start the-real-seb"
        echo "  - Detener:          systemctl --user stop the-real-seb"
        echo "  - Ver estado:       systemctl --user status the-real-seb"
        echo "  - Ver logs:         journalctl --user -u the-real-seb -f"
        echo ""
        echo -e "Ubicacion: ${BLUE}$SERVICE_FILE${NC}"
        echo ""
        echo "Para removerlo, ejecuta ./Setup/Linux/remove-from-startup.sh"
        echo ""

        read -p "Deseas iniciar el servicio ahora? (s/n): " START_NOW
        if [[ "$START_NOW" =~ ^[Ss]$ ]]; then
            systemctl --user start the-real-seb.service
            echo ""
            systemctl --user status the-real-seb.service --no-pager
        fi
        ;;

    *)
        echo -e "${RED}Opcion no valida.${NC}"
        exit 1
        ;;
esac

echo ""
