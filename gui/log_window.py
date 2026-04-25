"""
Ventana de logs con interfaz gráfica para el bot Music Maniac
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

    def create_image(self):
        """Crear un icono simple para el system tray"""
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
        self.window.title("Music Maniac - Bot Logs")
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
        self.text_area.insert(tk.END, "=== Music Maniac Bot Log Window ===\n")
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

    def setup_tray_icon(self):
        image = self.create_image()
        menu = pystray.Menu(
            pystray.MenuItem("Abrir Dashboard", self.open_dashboard, default=True),
            pystray.MenuItem("Mostrar/Ocultar Logs", self.toggle_window),
            pystray.MenuItem("Salir", self.quit_app)
        )
        self.icon = pystray.Icon("MusicManiac", image, "Music Maniac Bot", menu)

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
