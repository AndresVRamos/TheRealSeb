import asyncio
import maniac
import threading
import logging

# Silenciar logs de Flask/Werkzeug para que no contaminen los logs del bot
logging.getLogger('werkzeug').setLevel(logging.ERROR)
logging.getLogger('flask').setLevel(logging.ERROR)

# Importar dashboard web (con manejo de errores si no está disponible)
try:
    from gui.web.dashboard import app as dashboard_app, ensure_log_file
    DASHBOARD_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Dashboard web no disponible: {e}")
    DASHBOARD_AVAILABLE = False


def start_bot():
    """Iniciar el bot en un thread separado"""
    asyncio.run(maniac.run_bot())


def start_dashboard():
    """Iniciar el dashboard web en un thread separado"""
    if not DASHBOARD_AVAILABLE:
        return

    try:
        logging.info("=" * 70)
        logging.info("Iniciando Web Dashboard...")
        logging.info("Acceso local:  http://localhost:5000")
        logging.info("Acceso remoto: http://<IP_PUBLICA>:5000")
        logging.info("=" * 70)

        ensure_log_file()
        # use_reloader=False es necesario porque el reloader no funciona en threads
        dashboard_app.run(
            host='0.0.0.0',
            port=5000,
            debug=False,
            threaded=True,
            use_reloader=False
        )
    except Exception as e:
        logging.error(f"Error al iniciar Web Dashboard: {e}")
        logging.info("El bot continuará sin el dashboard.")
        logging.info("Puedes iniciarlo manualmente con: python gui/web/dashboard.py")


if __name__ == "__main__":
    # Iniciar el bot de Discord en un thread separado
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()

    # Iniciar el icono del system tray en un thread separado
    tray_thread = threading.Thread(target=maniac.log_window.run_tray, daemon=True)
    tray_thread.start()

    # Iniciar el dashboard web en un thread separado
    if DASHBOARD_AVAILABLE:
        dashboard_thread = threading.Thread(target=start_dashboard, daemon=True)
        dashboard_thread.start()
        logging.info("Dashboard web iniciado en background")
    else:
        logging.warning("Dashboard web no disponible - continuando sin él")

    # Ejecutar la ventana de logs en el thread principal (requerido por tkinter en Windows)
    maniac.log_window.run()
