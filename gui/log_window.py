"""
Ventana de logs con interfaz gráfica para el bot The Real Seb
"""
import tkinter as tk
from tkinter import scrolledtext
import threading
import pystray
from PIL import Image, ImageDraw
import os
import sys
import logging
import webbrowser


class TextHandler(logging.Handler):
    """Handler personalizado para capturar logs y mostrarlos en la GUI"""

    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        # Formatear el mensaje base
        msg = self.format(record)

        # Determinar el tag basado en el nivel
        level = record.levelname
        if level == 'ERROR' or level == 'CRITICAL':
            tag = 'error'
        elif level == 'WARNING':
            tag = 'warning'
        elif level == 'INFO':
            tag = 'info'
        elif level == 'DEBUG':
            tag = 'debug'
        else:
            tag = 'default'

        def append():
            if self.text_widget and self.text_widget.winfo_exists():
                self.text_widget.configure(state='normal')
                # Insertar todo el mensaje (incluyendo stack trace) con el mismo tag
                self.text_widget.insert(tk.END, msg + '\n', tag)
                self.text_widget.configure(state='disabled')
                self.text_widget.yview(tk.END)
        if self.text_widget:
            self.text_widget.after(0, append)


class StreamRedirector:
    """Clase para redirigir stdout/stderr al text widget con buffer"""

    def __init__(self, text_widget, stream_type='stdout'):
        self.text_widget = text_widget
        self.stream_type = stream_type
        self.tag = 'error' if stream_type == 'stderr' else 'default'
        self.buffer = ""
        self.flush_scheduled = False
        self.lock = threading.Lock()

    def write(self, text):
        if not text:
            return

        with self.lock:
            self.buffer += text

            # Programar flush si no está programado
            if not self.flush_scheduled and self.text_widget:
                self.flush_scheduled = True
                # Esperar 50ms para acumular más texto antes de mostrar
                self.text_widget.after(50, self._flush_buffer)

    def _flush_buffer(self):
        """Vaciar el buffer y mostrar todo el texto acumulado"""
        with self.lock:
            if not self.buffer:
                self.flush_scheduled = False
                return

            text_to_show = self.buffer
            self.buffer = ""
            self.flush_scheduled = False

        tag = self.tag

        def append():
            if self.text_widget and self.text_widget.winfo_exists():
                self.text_widget.configure(state='normal')
                self.text_widget.insert(tk.END, text_to_show, tag)
                self.text_widget.configure(state='disabled')
                self.text_widget.yview(tk.END)

        if self.text_widget:
            self.text_widget.after(0, append)

    def flush(self):
        """Forzar flush del buffer"""
        if self.buffer:
            self._flush_buffer()


class LogWindow:
    """Clase para la ventana de logs"""

    def __init__(self):
        self.window = None
        self.text_area = None
        self.icon = None
        self.is_visible = False
        self.pending_action = None
        self._update_available = False
        self._update_installing = False
        self._update_version = ""
        self._update_url = ""
        self._update_download_url = ""
        self._update_filename = ""

    def create_image(self):
        """Cargar el icono del system tray desde archivo"""
        try:
            # Obtener directorio raíz del proyecto
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

            # Buscar icon.ico en diferentes ubicaciones
            possible_paths = [
                os.path.join(base_dir, 'icon.ico'),  # Instalado (raíz)
                os.path.join(base_dir, 'Setup', 'Windows', 'icon.ico'),  # Desarrollo
            ]

            for icon_path in possible_paths:
                if os.path.exists(icon_path):
                    image = Image.open(icon_path)
                    # Redimensionar a 64x64 para el tray
                    image = image.resize((64, 64), Image.Resampling.LANCZOS)
                    return image
        except Exception:
            pass

        # Fallback: crear icono simple si no se encuentra el archivo
        width = 64
        height = 64
        color1 = (0, 120, 212)  # Azul
        color2 = (255, 255, 255)  # Blanco

        image = Image.new('RGB', (width, height), color1)
        dc = ImageDraw.Draw(image)

        # Nota musical simple
        dc.ellipse([20, 35, 35, 50], fill=color2)
        dc.rectangle([32, 15, 38, 42], fill=color2)

        return image

    def setup_window(self):
        """Configurar la ventana inicial"""
        self.window = tk.Tk()
        self.window.title("The Real Seb - Bot Logs")
        self.window.geometry("800x600")

        # Configurar el cierre de la ventana
        self.window.protocol("WM_DELETE_WINDOW", self.hide_window)

        # Crear área de texto con scroll
        self.text_area = scrolledtext.ScrolledText(
            self.window,
            state='disabled',
            bg='#1e1e1e',
            fg='#d4d4d4',
            font=('Consolas', 10),
            wrap=tk.WORD
        )
        self.text_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Configurar tags para colores según el nivel de log
        self.text_area.tag_config('error', foreground='#f44747')      # Rojo para errores
        self.text_area.tag_config('warning', foreground='#ff8c00')    # Naranja para warnings
        self.text_area.tag_config('info', foreground='#4fc3f7')       # Azul claro para info
        self.text_area.tag_config('debug', foreground='#a9a9a9')      # Gris para debug
        self.text_area.tag_config('default', foreground='#d4d4d4')    # Blanco/gris claro por defecto

        # Configurar logging para capturar todo
        text_handler = TextHandler(self.text_area)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        text_handler.setFormatter(formatter)

        # Configurar el logger raíz para capturar todos los logs
        root_logger = logging.getLogger()
        root_logger.addHandler(text_handler)
        root_logger.setLevel(logging.DEBUG)

        # Asegurarse de que yt-dlp también loggee
        logging.getLogger('yt_dlp').setLevel(logging.DEBUG)
        logging.getLogger('yt_dlp').addHandler(text_handler)

        # Redirigir stderr para capturar errores no manejados
        sys.stderr = StreamRedirector(self.text_area, 'stderr')

        # Instalar excepthooks para capturar excepciones no manejadas como logs
        self._original_excepthook = sys.excepthook
        sys.excepthook = self._custom_excepthook
        threading.excepthook = self._threading_excepthook

        # Mensaje de bienvenida
        self.text_area.configure(state='normal')
        self.text_area.insert(tk.END, "=== The Real Seb Bot Log Window ===\n")
        self.text_area.insert(tk.END, "Bot iniciado correctamente.\n\n")
        self.text_area.configure(state='disabled')

        # Inicialmente oculta
        self.window.withdraw()

    def toggle_window(self, icon=None, item=None):
        if self.is_visible:
            self.pending_action = 'hide'
        else:
            self.pending_action = 'show'

    def show_window(self):
        if self.window:
            self.window.deiconify()
            self.window.lift()
            self.window.focus_force()
            self.is_visible = True

    def hide_window(self):
        if self.window:
            self.window.withdraw()
            self.is_visible = False

    def open_dashboard(self, icon=None, item=None):
        """Abrir el dashboard web en el navegador predeterminado"""
        try:
            webbrowser.open('http://localhost:5000')
            logging.info("Dashboard web abierto en el navegador")
        except Exception as e:
            logging.error(f"Error al abrir dashboard: {e}")

    def _custom_excepthook(self, exc_type, exc_value, exc_traceback):
        """Capturar excepciones no manejadas y mostrarlas como un solo log"""
        if issubclass(exc_type, KeyboardInterrupt):
            # No loguear Ctrl+C
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        # Loguear la excepción completa como un solo registro
        logging.error(
            "Excepción no manejada",
            exc_info=(exc_type, exc_value, exc_traceback)
        )

    def _threading_excepthook(self, args):
        """Capturar excepciones en threads"""
        if args.exc_type == SystemExit:
            return

        logging.error(
            f"Excepción en thread '{args.thread.name}'",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback)
        )

    def check_pending_actions(self):
        """Revisar si hay acciones pendientes y ejecutarlas"""
        if self.pending_action == 'show':
            self.show_window()
            self.pending_action = None
        elif self.pending_action == 'hide':
            self.hide_window()
            self.pending_action = None

        # Volver a revisar en 100ms
        if self.window:
            self.window.after(100, self.check_pending_actions)

    def open_update_page(self, icon=None, item=None):
        """Abrir la página de releases para descargar la actualización"""
        if self._update_url:
            webbrowser.open(self._update_url)

    def notify_update(self, version: str, url: str, download_url: str = None, filename: str = None):
        """Llamado desde el updater cuando hay una versión nueva disponible"""
        self._update_available = True
        self._update_version = version
        self._update_url = url
        self._update_download_url = download_url or ""
        self._update_filename = filename or ""

        msg = (
            f"Versión {version} disponible. Haz clic en 'Actualizar ahora' en el menú del tray."
            if download_url else
            f"Versión {version} disponible. Abre el menú del tray para más información."
        )

        def _show_toast():
            try:
                from winotify import Notification
                toast = Notification(
                    app_id="The Real Seb",
                    title="Actualización disponible",
                    msg=msg,
                    duration="long"
                )
                if url:
                    toast.add_actions(label="Ver release", launch=url)
                toast.show()
            except Exception:
                pass

        threading.Thread(target=_show_toast, daemon=True).start()

        if self.icon:
            try:
                self.icon.notify(msg, "The Real Seb — Actualización disponible")
            except Exception:
                pass
            self.icon.update_menu()

    def _install_update(self, icon=None, item=None):
        """Dispara la descarga e instalación silenciosa"""
        if self._update_installing or not self._update_download_url:
            return
        self._update_installing = True
        self.icon.update_menu()
        from core.updater import start_install
        start_install(self._update_download_url, self._update_filename)

    def setup_tray_icon(self):
        image = self.create_image()
        menu = pystray.Menu(
            pystray.MenuItem("Abrir Dashboard", self.open_dashboard, default=True),
            pystray.MenuItem("Mostrar/Ocultar Logs", self.toggle_window),
            pystray.Menu.SEPARATOR,
            # Botón de instalación silenciosa (visible solo si hay update con .exe disponible)
            pystray.MenuItem(
                lambda item: (
                    "Instalando... esperá" if self._update_installing
                    else f"🔔 Actualizar ahora a v{self._update_version}"
                ),
                self._install_update,
                visible=lambda item: self._update_available and bool(self._update_download_url),
                enabled=lambda item: not self._update_installing
            ),
            # Fallback: abrir releases en el navegador si no hay .exe disponible
            pystray.MenuItem(
                lambda item: f"🔔 Ver actualización v{self._update_version}",
                self.open_update_page,
                visible=lambda item: self._update_available and not bool(self._update_download_url)
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Reiniciar", self.restart_app),
            pystray.MenuItem("Salir", self.quit_app)
        )
        self.icon = pystray.Icon("TheRealSeb", image, "The Real Seb Bot", menu)

    def restart_app(self, icon=None, item=None):
        """Reiniciar el bot"""
        import subprocess
        if self.icon:
            self.icon.stop()
        if self.window:
            self.window.quit()

        # Obtener el comando para reiniciar
        if getattr(sys, 'frozen', False):
            # Ejecutable empaquetado
            subprocess.Popen([sys.executable])
        else:
            # Script de Python
            subprocess.Popen([sys.executable] + sys.argv)

        os._exit(0)

    def quit_app(self, icon=None, item=None):
        if self.icon:
            self.icon.stop()
        if self.window:
            self.window.quit()
        os._exit(0)

    def run_tray(self):
        """El tray icon corre en un thread separado"""
        self.setup_tray_icon()
        self.icon.run()

    def run(self):
        """Ejecutar la aplicación en el thread principal"""
        self.setup_window()
        self.check_pending_actions()
        self.window.mainloop()
