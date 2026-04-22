"""
Web Dashboard - Servidor web para monitorear el bot en tiempo real

Estructura del proyecto:
gui/web/
├── dashboard.py (este archivo)
├── views/
│   ├── base.html (template base)
│   └── logs.html (vista de logs)
└── static/
    ├── css/ (estilos)
    └── js/ (scripts)

Uso: python gui/web/dashboard.py
Acceso: http://localhost:5000 (local) o http://IP_PUBLICA:5000 (remoto)
"""
import os
import time
from flask import Flask, render_template, Response, jsonify, redirect
from datetime import datetime

# Obtener rutas del proyecto
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))

# Inicializar Flask con rutas correctas
app = Flask(__name__,
            static_folder=os.path.join(CURRENT_DIR, 'static'),
            static_url_path='/static',
            template_folder=os.path.join(CURRENT_DIR, 'views'))

# Configuración
LOG_FILE = os.path.join(PROJECT_ROOT, "data", "bot.log")
MAX_LINES = 1000  # Máximo de líneas a mostrar inicialmente


def ensure_log_file():
    """Asegura que el archivo de logs exista"""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            f.write(f"=== Music Maniac Bot Logs - {datetime.now().isoformat()} ===\n")


@app.route('/')
def index():
    """Redirige a la página de logs por defecto"""
    return redirect('/logs')


@app.route('/logs')
def logs():
    """Visualizador de logs en tiempo real"""
    return render_template('logs.html')


@app.route('/api/logs/initial')
def get_initial_logs():
    """Obtiene las últimas N líneas del archivo de logs"""
    ensure_log_file()

    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # Tomar las últimas MAX_LINES líneas
            initial_lines = lines[-MAX_LINES:] if len(lines) > MAX_LINES else lines
            return jsonify({
                'lines': [line.rstrip('\n') for line in initial_lines],
                'total': len(lines)
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/logs/stream')
def stream_logs():
    """Stream de logs en tiempo real usando Server-Sent Events"""
    ensure_log_file()

    def generate():
        """Generador que lee nuevas líneas del archivo"""
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                # Ir al final del archivo
                f.seek(0, os.SEEK_END)

                while True:
                    line = f.readline()
                    if line:
                        # Enviar la línea como evento SSE
                        yield f"data: {line.rstrip()}\n\n"
                    else:
                        # No hay nuevas líneas, esperar un poco
                        time.sleep(0.5)
        except GeneratorExit:
            # El cliente se desconectó, cerrar limpiamente
            pass
        except Exception as e:
            # Cualquier otro error, registrarlo
            print(f"Error en stream de logs: {e}")

    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/stats')
def get_stats():
    """Obtiene estadísticas básicas del archivo de logs"""
    ensure_log_file()

    try:
        # Tamaño del archivo
        file_size = os.path.getsize(LOG_FILE)

        # Contar líneas y niveles
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            total_lines = len(lines)

            # Contar por nivel
            errors = sum(1 for line in lines if 'ERROR' in line or 'CRITICAL' in line)
            warnings = sum(1 for line in lines if 'WARNING' in line)
            info = sum(1 for line in lines if 'INFO' in line)

        # Última modificación
        last_modified = datetime.fromtimestamp(os.path.getmtime(LOG_FILE)).isoformat()

        return jsonify({
            'file_size': file_size,
            'file_size_mb': round(file_size / (1024 * 1024), 2),
            'total_lines': total_lines,
            'errors': errors,
            'warnings': warnings,
            'info': info,
            'last_modified': last_modified
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/clear')
def clear_logs():
    """Limpia el archivo de logs (requiere confirmación)"""
    try:
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            f.write(f"=== Logs limpiados - {datetime.now().isoformat()} ===\n")
        return jsonify({'success': True, 'message': 'Logs limpiados correctamente'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'log_file': LOG_FILE,
        'log_exists': os.path.exists(LOG_FILE)
    })


if __name__ == '__main__':
    ensure_log_file()

    print("=" * 70)
    print("🎵 The Real Seb - Web Dashboard")
    print("=" * 70)
    print(f"📁 Archivo de logs: {os.path.abspath(LOG_FILE)}")
    print(f"📂 Views: {os.path.abspath(os.path.join(CURRENT_DIR, 'views'))}")
    print(f"📂 Static files: {os.path.abspath(os.path.join(CURRENT_DIR, 'static'))}")
    print(f"\n🌐 Servidor local:  http://localhost:5000")
    print(f"🌐 Acceso remoto:   http://<IP_PUBLICA>:5000")
    print(f"\n📊 Endpoints disponibles:")
    print(f"   GET  /              - Redirige a /logs")
    print(f"   GET  /logs          - Visualizador de logs")
    print(f"   GET  /api/logs/initial - Logs iniciales")
    print(f"   GET  /api/logs/stream  - Stream en tiempo real")
    print(f"   GET  /api/stats       - Estadísticas")
    print(f"   GET  /api/clear       - Limpiar logs")
    print(f"   GET  /health          - Health check")
    print("=" * 70)
    print("\nPresiona Ctrl+C para detener el servidor\n")

    # Ejecutar servidor
    # host='0.0.0.0' permite acceso desde cualquier IP
    # Para mayor seguridad en producción, usar host='127.0.0.1' (solo local)
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
