import asyncio
import maniac
import threading

def start_bot():
    """Iniciar el bot en un thread separado"""
    asyncio.run(maniac.run_bot())

if __name__ == "__main__":
    # Iniciar el bot de Discord en un thread separado
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()

    # Iniciar el icono del system tray en un thread separado
    tray_thread = threading.Thread(target=maniac.log_window.run_tray, daemon=True)
    tray_thread.start()

    # Ejecutar la ventana de logs en el thread principal (requerido por tkinter en Windows)
    maniac.log_window.run()
