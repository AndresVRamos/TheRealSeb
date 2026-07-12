"""
Web Dashboard - Servidor web para monitorear el bot en tiempo real

Estructura del proyecto:
gui/web/
├── dashboard.py (este archivo)
├── views/
│   ├── base.html (template base)
│   ├── home.html (vista principal)
│   └── logs.html (vista de logs)
└── static/
    ├── css/ (estilos)
    └── js/ (scripts)

Uso: python gui/web/dashboard.py
Acceso: http://localhost:5000 (local) o http://IP_PUBLICA:5000 (remoto)
"""
import os
import sys
import time
from flask import Flask, render_template, Response, jsonify, redirect, request
from datetime import datetime, timedelta

# Obtener rutas del proyecto
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))

# Agregar PROJECT_ROOT al path para importar modulos del bot
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Importar funciones de base de datos (con manejo de errores)
try:
    from core.database.schema import get_connection
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

# Variable global para estado del bot y tiempo de inicio
bot_start_time = None
bot_instance = None


def set_bot_instance(bot):
    """Establecer instancia del bot para acceder a su estado"""
    global bot_instance, bot_start_time
    bot_instance = bot
    bot_start_time = datetime.now()

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
            f.write(f"=== The Real Seb Bot Logs - {datetime.now().isoformat()} ===\n")


@app.route('/')
def index():
    """Redirige a la página principal"""
    return redirect('/home')


@app.route('/home')
def home():
    """Vista principal del dashboard"""
    return render_template('home.html')


@app.route('/logs')
def logs():
    """Visualizador de logs en tiempo real"""
    return render_template('logs.html')


@app.route('/stats')
def stats():
    """Vista de estadisticas con graficos"""
    return render_template('stats.html')


@app.route('/servers')
def servers():
    """Vista de servidores conectados"""
    return render_template('servers.html')


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


# ============================================
# API ENDPOINTS PARA HOME
# ============================================

@app.route('/api/home/stats')
def get_home_stats():
    """Obtiene estadisticas globales para la vista Home"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 500

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Estadisticas globales
        cursor.execute('''
            SELECT
                COUNT(*) as total_plays,
                COALESCE(SUM(t.duration_seconds), 0) as total_time,
                COUNT(DISTINCT t.id) as unique_tracks,
                COUNT(DISTINCT t.artist_id) as unique_artists,
                MIN(p.played_at) as first_play,
                MAX(p.played_at) as last_play
            FROM plays p
            JOIN tracks t ON p.track_id = t.id
        ''')
        row = cursor.fetchone()

        # Contar guilds
        cursor.execute('SELECT COUNT(*) as count FROM guilds')
        guild_count = cursor.fetchone()['count']

        conn.close()

        # Calcular uptime
        uptime_str = '--'
        if bot_start_time:
            delta = datetime.now() - bot_start_time
            hours, remainder = divmod(int(delta.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)
            if hours > 0:
                uptime_str = f"{hours}h {minutes}m"
            else:
                uptime_str = f"{minutes}m"

        # Verificar si el bot esta online
        bot_online = bot_instance is not None and not bot_instance.is_closed()

        return jsonify({
            'total_plays': row['total_plays'],
            'total_time': row['total_time'],
            'unique_tracks': row['unique_tracks'],
            'unique_artists': row['unique_artists'],
            'first_play': row['first_play'],
            'last_play': row['last_play'],
            'guild_count': guild_count,
            'uptime': uptime_str,
            'bot_online': bot_online
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/home/recent')
def get_recent_plays():
    """Obtiene las reproducciones mas recientes"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 500

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT
                t.title,
                a.name as artist,
                p.played_at
            FROM plays p
            JOIN tracks t ON p.track_id = t.id
            LEFT JOIN artists a ON t.artist_id = a.id
            ORDER BY p.played_at DESC
            LIMIT 10
        ''')
        rows = cursor.fetchall()
        conn.close()

        plays = [{
            'title': row['title'],
            'artist': row['artist'],
            'played_at': row['played_at']
        } for row in rows]

        return jsonify({'plays': plays})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/home/top-songs')
def get_top_songs():
    """Obtiene las canciones mas reproducidas"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 500

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT
                t.title,
                COUNT(*) as plays
            FROM plays p
            JOIN tracks t ON p.track_id = t.id
            GROUP BY t.id
            ORDER BY plays DESC
            LIMIT 10
        ''')
        rows = cursor.fetchall()
        conn.close()

        songs = [{
            'title': row['title'],
            'plays': row['plays']
        } for row in rows]

        return jsonify({'songs': songs})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/home/top-artists')
def get_top_artists():
    """Obtiene los artistas mas reproducidos"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 500

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT
                a.name,
                COUNT(*) as plays
            FROM plays p
            JOIN tracks t ON p.track_id = t.id
            JOIN artists a ON t.artist_id = a.id
            GROUP BY a.id
            ORDER BY plays DESC
            LIMIT 10
        ''')
        rows = cursor.fetchall()
        conn.close()

        artists = [{
            'name': row['name'],
            'plays': row['plays']
        } for row in rows]

        return jsonify({'artists': artists})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================
# API ENDPOINTS PARA STATS (GRAFICOS)
# ============================================

@app.route('/api/stats/trend')
def get_stats_trend():
    """Obtiene tendencia de reproducciones por dia"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 500

    days = request.args.get('days', 7, type=int)
    days = min(days, 365)  # Maximo 1 año
    guild_id = request.args.get('guild_id', type=int)

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Obtener plays por dia (con filtro opcional de servidor)
        if guild_id:
            cursor.execute('''
                SELECT DATE(played_at) as date, COUNT(*) as plays
                FROM plays
                WHERE played_at >= DATE('now', ?) AND guild_id = ?
                GROUP BY DATE(played_at)
                ORDER BY date ASC
            ''', (f'-{days} days', guild_id))
        else:
            cursor.execute('''
                SELECT DATE(played_at) as date, COUNT(*) as plays
                FROM plays
                WHERE played_at >= DATE('now', ?)
                GROUP BY DATE(played_at)
                ORDER BY date ASC
            ''', (f'-{days} days',))
        rows = cursor.fetchall()
        conn.close()

        # Crear diccionario con todos los dias (incluyendo dias sin plays)
        date_counts = {row['date']: row['plays'] for row in rows}

        labels = []
        values = []
        for i in range(days, -1, -1):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            labels.append((datetime.now() - timedelta(days=i)).strftime('%d/%m'))
            values.append(date_counts.get(date, 0))

        return jsonify({'labels': labels, 'values': values})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats/hourly')
def get_stats_hourly():
    """Obtiene reproducciones por hora del dia (totales y promedio)"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 500

    days = request.args.get('days', 7, type=int)
    days = min(days, 365)
    guild_id = request.args.get('guild_id', type=int)

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Obtener plays por hora
        if guild_id:
            cursor.execute('''
                SELECT CAST(strftime('%H', played_at) AS INTEGER) as hour, COUNT(*) as plays
                FROM plays
                WHERE played_at >= DATE('now', ?) AND guild_id = ?
                GROUP BY hour
                ORDER BY hour ASC
            ''', (f'-{days} days', guild_id))
        else:
            cursor.execute('''
                SELECT CAST(strftime('%H', played_at) AS INTEGER) as hour, COUNT(*) as plays
                FROM plays
                WHERE played_at >= DATE('now', ?)
                GROUP BY hour
                ORDER BY hour ASC
            ''', (f'-{days} days',))
        rows = cursor.fetchall()

        # Contar dias con actividad
        if guild_id:
            cursor.execute('''
                SELECT COUNT(DISTINCT DATE(played_at)) as active_days
                FROM plays
                WHERE played_at >= DATE('now', ?) AND guild_id = ?
            ''', (f'-{days} days', guild_id))
        else:
            cursor.execute('''
                SELECT COUNT(DISTINCT DATE(played_at)) as active_days
                FROM plays
                WHERE played_at >= DATE('now', ?)
            ''', (f'-{days} days',))
        active_days_row = cursor.fetchone()
        active_days = active_days_row['active_days'] if active_days_row else 1
        active_days = max(active_days, 1)

        conn.close()

        # Crear array con todas las horas (0-23)
        hour_counts = {row['hour']: row['plays'] for row in rows}

        labels = [f'{h:02d}:00' for h in range(24)]
        totals = [hour_counts.get(h, 0) for h in range(24)]
        # Promedio = total / dias con actividad (no todos los dias del rango)
        averages = [round(hour_counts.get(h, 0) / active_days, 1) for h in range(24)]

        return jsonify({
            'labels': labels,
            'values': totals,
            'totals': totals,
            'averages': averages,
            'active_days': active_days
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats/daily')
def get_stats_daily():
    """Obtiene reproducciones por dia de la semana (totales y promedio)"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 500

    days = request.args.get('days', 7, type=int)
    days = min(days, 365)
    guild_id = request.args.get('guild_id', type=int)

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # SQLite: 0=Sunday, 1=Monday, etc.
        if guild_id:
            cursor.execute('''
                SELECT CAST(strftime('%w', played_at) AS INTEGER) as dow, COUNT(*) as plays
                FROM plays
                WHERE played_at >= DATE('now', ?) AND guild_id = ?
                GROUP BY dow
                ORDER BY dow ASC
            ''', (f'-{days} days', guild_id))
        else:
            cursor.execute('''
                SELECT CAST(strftime('%w', played_at) AS INTEGER) as dow, COUNT(*) as plays
                FROM plays
                WHERE played_at >= DATE('now', ?)
                GROUP BY dow
                ORDER BY dow ASC
            ''', (f'-{days} days',))
        rows = cursor.fetchall()

        # Contar dias activos por dia de la semana (ej: cuantos lunes tuvieron actividad)
        if guild_id:
            cursor.execute('''
                SELECT
                    CAST(strftime('%w', played_at) AS INTEGER) as dow,
                    COUNT(DISTINCT DATE(played_at)) as active_count
                FROM plays
                WHERE played_at >= DATE('now', ?) AND guild_id = ?
                GROUP BY dow
            ''', (f'-{days} days', guild_id))
        else:
            cursor.execute('''
                SELECT
                    CAST(strftime('%w', played_at) AS INTEGER) as dow,
                    COUNT(DISTINCT DATE(played_at)) as active_count
                FROM plays
                WHERE played_at >= DATE('now', ?)
                GROUP BY dow
            ''', (f'-{days} days',))
        dow_active_rows = cursor.fetchall()
        conn.close()

        # Mapear dias activos por dia de la semana
        dow_active = {row['dow']: row['active_count'] for row in dow_active_rows}

        # Mapear a nombres de dias (empezando en Lunes)
        day_names = ['Dom', 'Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab']
        dow_counts = {row['dow']: row['plays'] for row in rows}

        # Reordenar para que empiece en Lunes
        order = [1, 2, 3, 4, 5, 6, 0]  # Lun, Mar, Mie, Jue, Vie, Sab, Dom
        labels = [day_names[i] for i in order]
        totals = [dow_counts.get(i, 0) for i in order]
        # Promedio = total / dias activos de ese dia de la semana
        averages = []
        for i in order:
            active = dow_active.get(i, 1)
            active = max(active, 1)  # Evitar division por cero
            avg = round(dow_counts.get(i, 0) / active, 1)
            averages.append(avg)

        return jsonify({
            'labels': labels,
            'values': totals,
            'totals': totals,
            'averages': averages
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats/top-artists')
def get_stats_top_artists():
    """Obtiene top artistas para el grafico"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 500

    days = request.args.get('days', 7, type=int)
    days = min(days, 365)
    limit = request.args.get('limit', 5, type=int)
    guild_id = request.args.get('guild_id', type=int)

    try:
        conn = get_connection()
        cursor = conn.cursor()

        if guild_id:
            cursor.execute('''
                SELECT a.name, COUNT(*) as plays
                FROM plays p
                JOIN tracks t ON p.track_id = t.id
                JOIN artists a ON t.artist_id = a.id
                WHERE p.played_at >= DATE('now', ?) AND p.guild_id = ?
                GROUP BY a.id
                ORDER BY plays DESC
                LIMIT ?
            ''', (f'-{days} days', guild_id, limit))
        else:
            cursor.execute('''
                SELECT a.name, COUNT(*) as plays
                FROM plays p
                JOIN tracks t ON p.track_id = t.id
                JOIN artists a ON t.artist_id = a.id
                WHERE p.played_at >= DATE('now', ?)
                GROUP BY a.id
                ORDER BY plays DESC
                LIMIT ?
            ''', (f'-{days} days', limit))
        rows = cursor.fetchall()
        conn.close()

        labels = [row['name'] for row in rows]
        values = [row['plays'] for row in rows]

        return jsonify({'labels': labels, 'values': values})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats/top-users')
def get_stats_top_users():
    """Obtiene top usuarios por reproducciones"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 500

    days = request.args.get('days', 7, type=int)
    days = min(days, 365)
    limit = request.args.get('limit', 5, type=int)
    guild_id = request.args.get('guild_id', type=int)

    try:
        conn = get_connection()
        cursor = conn.cursor()

        if guild_id:
            cursor.execute('''
                SELECT u.display_name, u.username, COUNT(*) as plays
                FROM plays p
                JOIN users u ON p.requester_id = u.id
                WHERE p.played_at >= DATE('now', ?) AND p.guild_id = ?
                GROUP BY u.id
                ORDER BY plays DESC
                LIMIT ?
            ''', (f'-{days} days', guild_id, limit))
        else:
            cursor.execute('''
                SELECT u.display_name, u.username, COUNT(*) as plays
                FROM plays p
                JOIN users u ON p.requester_id = u.id
                WHERE p.played_at >= DATE('now', ?)
                GROUP BY u.id
                ORDER BY plays DESC
                LIMIT ?
            ''', (f'-{days} days', limit))
        rows = cursor.fetchall()
        conn.close()

        labels = [row['display_name'] or row['username'] for row in rows]
        values = [row['plays'] for row in rows]

        return jsonify({'labels': labels, 'values': values})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats/active-users')
def get_stats_active_users():
    """Obtiene usuarios activos por dia"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 500

    days = request.args.get('days', 7, type=int)
    days = min(days, 365)
    guild_id = request.args.get('guild_id', type=int)

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Usuarios unicos por dia
        if guild_id:
            cursor.execute('''
                SELECT DATE(played_at) as date, COUNT(DISTINCT requester_id) as users
                FROM plays
                WHERE played_at >= DATE('now', ?) AND guild_id = ?
                GROUP BY DATE(played_at)
                ORDER BY date ASC
            ''', (f'-{days} days', guild_id))
        else:
            cursor.execute('''
                SELECT DATE(played_at) as date, COUNT(DISTINCT requester_id) as users
                FROM plays
                WHERE played_at >= DATE('now', ?)
                GROUP BY DATE(played_at)
                ORDER BY date ASC
            ''', (f'-{days} days',))
        rows = cursor.fetchall()
        conn.close()

        # Crear diccionario con todos los dias
        date_counts = {row['date']: row['users'] for row in rows}

        labels = []
        values = []
        for i in range(days, -1, -1):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            labels.append((datetime.now() - timedelta(days=i)).strftime('%d/%m'))
            values.append(date_counts.get(date, 0))

        return jsonify({'labels': labels, 'values': values})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats/active-users-detail')
def get_active_users_detail():
    """Obtiene lista de usuarios activos en un dia especifico"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 500

    date = request.args.get('date')
    if not date:
        return jsonify({'error': 'Date parameter required'}), 400

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Obtener usuarios que hicieron reproducciones ese dia con su conteo
        cursor.execute('''
            SELECT
                u.display_name,
                u.username,
                COUNT(*) as plays
            FROM plays p
            JOIN users u ON p.requester_id = u.id
            WHERE DATE(p.played_at) = ?
            GROUP BY u.id
            ORDER BY plays DESC
        ''', (date,))
        users = cursor.fetchall()
        conn.close()

        result = [{
            'name': user['display_name'] or user['username'],
            'plays': user['plays']
        } for user in users]

        return jsonify({'users': result, 'date': date, 'total': len(result)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats/day-detail')
def get_day_detail():
    """Obtiene detalles de reproducciones de un dia especifico"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 500

    date = request.args.get('date')
    if not date:
        return jsonify({'error': 'Date parameter required'}), 400

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Obtener reproducciones del dia con info de listeners
        cursor.execute('''
            SELECT
                p.id as play_id,
                t.title,
                a.name as artist,
                p.played_at,
                u.display_name as requester_display,
                u.username as requester_username
            FROM plays p
            JOIN tracks t ON p.track_id = t.id
            LEFT JOIN artists a ON t.artist_id = a.id
            JOIN users u ON p.requester_id = u.id
            WHERE DATE(p.played_at) = ?
            ORDER BY p.played_at ASC
        ''', (date,))
        plays = cursor.fetchall()

        # Para cada play, obtener los listeners
        result = []
        for play in plays:
            # Obtener listeners de esta reproduccion
            cursor.execute('''
                SELECT u.display_name, u.username
                FROM listens l
                JOIN users u ON l.user_id = u.id
                WHERE l.play_id = ?
            ''', (play['play_id'],))
            listeners = cursor.fetchall()

            listener_names = [l['display_name'] or l['username'] for l in listeners]

            result.append({
                'time': play['played_at'].split(' ')[1][:5] if ' ' in play['played_at'] else play['played_at'],
                'title': play['title'],
                'artist': play['artist'] or 'Desconocido',
                'requester': play['requester_display'] or play['requester_username'],
                'listeners_count': len(listener_names),
                'listeners_names': listener_names
            })

        conn.close()
        return jsonify({'plays': result, 'date': date})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================
# API ENDPOINTS PARA SERVERS
# ============================================

@app.route('/api/servers')
def get_servers_list():
    """Obtiene lista de servidores con estadisticas"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 500

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT
                g.id,
                g.discord_id,
                g.name,
                g.icon_url,
                g.total_plays,
                g.total_time_seconds,
                COUNT(DISTINCT p.requester_id) as total_users
            FROM guilds g
            LEFT JOIN plays p ON g.id = p.guild_id
            GROUP BY g.id
            ORDER BY g.total_plays DESC
        ''')
        rows = cursor.fetchall()
        conn.close()

        servers = [{
            'id': row['id'],
            'discord_id': row['discord_id'],
            'name': row['name'],
            'icon_url': row['icon_url'],
            'total_plays': row['total_plays'] or 0,
            'total_time': row['total_time_seconds'] or 0,
            'total_users': row['total_users'] or 0
        } for row in rows]

        return jsonify({'servers': servers})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/servers/<int:server_id>')
def get_server_detail(server_id):
    """Obtiene detalles de un servidor especifico"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 500

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Info basica del servidor
        cursor.execute('''
            SELECT
                g.id,
                g.discord_id,
                g.name,
                g.icon_url,
                g.total_plays,
                g.total_time_seconds
            FROM guilds g
            WHERE g.id = ?
        ''', (server_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return jsonify({'error': 'Server not found'}), 404

        # Contar usuarios unicos
        cursor.execute('''
            SELECT COUNT(DISTINCT requester_id) as total_users
            FROM plays
            WHERE guild_id = ?
        ''', (server_id,))
        users_row = cursor.fetchone()
        conn.close()

        return jsonify({
            'id': row['id'],
            'discord_id': row['discord_id'],
            'name': row['name'],
            'icon_url': row['icon_url'],
            'total_plays': row['total_plays'] or 0,
            'total_time': row['total_time_seconds'] or 0,
            'total_users': users_row['total_users'] or 0
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/servers/<int:server_id>/songs')
def get_server_top_songs(server_id):
    """Obtiene top canciones de un servidor"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 500

    limit = request.args.get('limit', 10, type=int)

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT
                t.title,
                a.name as artist,
                COUNT(*) as plays
            FROM plays p
            JOIN tracks t ON p.track_id = t.id
            LEFT JOIN artists a ON t.artist_id = a.id
            WHERE p.guild_id = ?
            GROUP BY t.id
            ORDER BY plays DESC
            LIMIT ?
        ''', (server_id, limit))
        rows = cursor.fetchall()
        conn.close()

        items = [{
            'title': row['title'],
            'artist': row['artist'],
            'plays': row['plays']
        } for row in rows]

        return jsonify({'items': items})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/servers/<int:server_id>/artists')
def get_server_top_artists(server_id):
    """Obtiene top artistas de un servidor"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 500

    limit = request.args.get('limit', 10, type=int)

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT
                a.name,
                COUNT(*) as plays
            FROM plays p
            JOIN tracks t ON p.track_id = t.id
            JOIN artists a ON t.artist_id = a.id
            WHERE p.guild_id = ?
            GROUP BY a.id
            ORDER BY plays DESC
            LIMIT ?
        ''', (server_id, limit))
        rows = cursor.fetchall()
        conn.close()

        items = [{
            'name': row['name'],
            'plays': row['plays']
        } for row in rows]

        return jsonify({'items': items})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/servers/<int:server_id>/users')
def get_server_top_users(server_id):
    """Obtiene todos los usuarios de un servidor ordenados por plays"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 500

    # Sin limite por defecto para mostrar todos los usuarios
    limit = request.args.get('limit', 1000, type=int)

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT
                u.display_name,
                u.username,
                COUNT(*) as plays
            FROM plays p
            JOIN users u ON p.requester_id = u.id
            WHERE p.guild_id = ?
            GROUP BY u.id
            ORDER BY plays DESC
            LIMIT ?
        ''', (server_id, limit))
        rows = cursor.fetchall()
        conn.close()

        items = [{
            'name': row['display_name'] or row['username'],
            'plays': row['plays']
        } for row in rows]

        return jsonify({'items': items})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================
# API ENDPOINTS PARA USUARIOS
# ============================================

@app.route('/api/users')
def get_users_list():
    """Obtiene lista de usuarios con estadisticas"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 500

    limit = request.args.get('limit', 50, type=int)

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT
                u.id,
                u.discord_id,
                u.display_name,
                u.username,
                u.avatar_url,
                COUNT(p.id) as total_plays,
                COALESCE(SUM(t.duration_seconds), 0) as total_time
            FROM users u
            LEFT JOIN plays p ON u.id = p.requester_id
            LEFT JOIN tracks t ON p.track_id = t.id
            GROUP BY u.id
            ORDER BY total_plays DESC
            LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        conn.close()

        users = [{
            'id': row['id'],
            'discord_id': row['discord_id'],
            'name': row['display_name'] or row['username'],
            'avatar_url': row['avatar_url'],
            'total_plays': row['total_plays'] or 0,
            'total_time': row['total_time'] or 0
        } for row in rows]

        return jsonify({'users': users})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/users/<int:user_id>')
def get_user_profile(user_id):
    """Obtiene perfil completo de un usuario"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 500

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Info basica del usuario
        cursor.execute('''
            SELECT
                u.id,
                u.discord_id,
                u.display_name,
                u.username,
                u.avatar_url
            FROM users u
            WHERE u.id = ?
        ''', (user_id,))
        user = cursor.fetchone()

        if not user:
            conn.close()
            return jsonify({'error': 'User not found'}), 404

        # Estadisticas generales
        cursor.execute('''
            SELECT
                COUNT(p.id) as total_plays,
                COALESCE(SUM(t.duration_seconds), 0) as total_time,
                COUNT(DISTINCT t.id) as unique_tracks,
                COUNT(DISTINCT t.artist_id) as unique_artists,
                MIN(p.played_at) as first_play,
                MAX(p.played_at) as last_play
            FROM plays p
            JOIN tracks t ON p.track_id = t.id
            WHERE p.requester_id = ?
        ''', (user_id,))
        stats = cursor.fetchone()

        # Top canciones
        cursor.execute('''
            SELECT t.title, a.name as artist, COUNT(*) as plays
            FROM plays p
            JOIN tracks t ON p.track_id = t.id
            LEFT JOIN artists a ON t.artist_id = a.id
            WHERE p.requester_id = ?
            GROUP BY t.id
            ORDER BY plays DESC
            LIMIT 5
        ''', (user_id,))
        top_songs = cursor.fetchall()

        # Top artistas
        cursor.execute('''
            SELECT a.name, COUNT(*) as plays
            FROM plays p
            JOIN tracks t ON p.track_id = t.id
            JOIN artists a ON t.artist_id = a.id
            WHERE p.requester_id = ?
            GROUP BY a.id
            ORDER BY plays DESC
            LIMIT 5
        ''', (user_id,))
        top_artists = cursor.fetchall()

        # Hora favorita
        cursor.execute('''
            SELECT CAST(strftime('%H', played_at) AS INTEGER) as hour, COUNT(*) as plays
            FROM plays
            WHERE requester_id = ?
            GROUP BY hour
            ORDER BY plays DESC
            LIMIT 1
        ''', (user_id,))
        fav_hour_row = cursor.fetchone()
        fav_hour = fav_hour_row['hour'] if fav_hour_row else None

        # Dia favorito
        cursor.execute('''
            SELECT CAST(strftime('%w', played_at) AS INTEGER) as dow, COUNT(*) as plays
            FROM plays
            WHERE requester_id = ?
            GROUP BY dow
            ORDER BY plays DESC
            LIMIT 1
        ''', (user_id,))
        fav_dow_row = cursor.fetchone()
        day_names = ['Domingo', 'Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado']
        fav_day = day_names[fav_dow_row['dow']] if fav_dow_row else None

        # Actividad reciente (ultimos 7 dias)
        cursor.execute('''
            SELECT DATE(played_at) as date, COUNT(*) as plays
            FROM plays
            WHERE requester_id = ? AND played_at >= DATE('now', '-7 days')
            GROUP BY DATE(played_at)
            ORDER BY date ASC
        ''', (user_id,))
        recent_activity = cursor.fetchall()

        conn.close()

        return jsonify({
            'id': user['id'],
            'discord_id': user['discord_id'],
            'name': user['display_name'] or user['username'],
            'avatar_url': user['avatar_url'],
            'stats': {
                'total_plays': stats['total_plays'] or 0,
                'total_time': stats['total_time'] or 0,
                'unique_tracks': stats['unique_tracks'] or 0,
                'unique_artists': stats['unique_artists'] or 0,
                'first_play': stats['first_play'],
                'last_play': stats['last_play'],
                'favorite_hour': fav_hour,
                'favorite_day': fav_day
            },
            'top_songs': [{
                'title': row['title'],
                'artist': row['artist'],
                'plays': row['plays']
            } for row in top_songs],
            'top_artists': [{
                'name': row['name'],
                'plays': row['plays']
            } for row in top_artists],
            'recent_activity': [{
                'date': row['date'],
                'plays': row['plays']
            } for row in recent_activity]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/users/by-name/<name>')
def get_user_by_name(name):
    """Busca usuario por nombre"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 500

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id FROM users
            WHERE display_name = ? OR username = ?
            LIMIT 1
        ''', (name, name))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({'id': row['id']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/compare/users')
def compare_users():
    """Compara estadisticas de dos usuarios"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 500

    user1_id = request.args.get('user1', type=int)
    user2_id = request.args.get('user2', type=int)
    days = request.args.get('days', 30, type=int)

    if not user1_id or not user2_id:
        return jsonify({'error': 'Two user IDs required'}), 400

    try:
        conn = get_connection()
        cursor = conn.cursor()

        users_data = []
        for user_id in [user1_id, user2_id]:
            # Info basica
            cursor.execute('''
                SELECT display_name, username, avatar_url
                FROM users WHERE id = ?
            ''', (user_id,))
            user = cursor.fetchone()

            if not user:
                conn.close()
                return jsonify({'error': f'User {user_id} not found'}), 404

            # Stats en el periodo
            cursor.execute('''
                SELECT
                    COUNT(p.id) as total_plays,
                    COALESCE(SUM(t.duration_seconds), 0) as total_time,
                    COUNT(DISTINCT t.id) as unique_tracks,
                    COUNT(DISTINCT t.artist_id) as unique_artists
                FROM plays p
                JOIN tracks t ON p.track_id = t.id
                WHERE p.requester_id = ? AND p.played_at >= DATE('now', ?)
            ''', (user_id, f'-{days} days'))
            stats = cursor.fetchone()

            # Top artista
            cursor.execute('''
                SELECT a.name, COUNT(*) as plays
                FROM plays p
                JOIN tracks t ON p.track_id = t.id
                JOIN artists a ON t.artist_id = a.id
                WHERE p.requester_id = ? AND p.played_at >= DATE('now', ?)
                GROUP BY a.id
                ORDER BY plays DESC
                LIMIT 1
            ''', (user_id, f'-{days} days'))
            top_artist = cursor.fetchone()

            # Top cancion
            cursor.execute('''
                SELECT t.title, COUNT(*) as plays
                FROM plays p
                JOIN tracks t ON p.track_id = t.id
                WHERE p.requester_id = ? AND p.played_at >= DATE('now', ?)
                GROUP BY t.id
                ORDER BY plays DESC
                LIMIT 1
            ''', (user_id, f'-{days} days'))
            top_song = cursor.fetchone()

            # Hora mas activa
            cursor.execute('''
                SELECT CAST(strftime('%H', played_at) AS INTEGER) as hour, COUNT(*) as plays
                FROM plays
                WHERE requester_id = ? AND played_at >= DATE('now', ?)
                GROUP BY hour
                ORDER BY plays DESC
                LIMIT 1
            ''', (user_id, f'-{days} days'))
            top_hour = cursor.fetchone()

            users_data.append({
                'id': user_id,
                'name': user['display_name'] or user['username'],
                'avatar_url': user['avatar_url'],
                'total_plays': stats['total_plays'] or 0,
                'total_time': stats['total_time'] or 0,
                'unique_tracks': stats['unique_tracks'] or 0,
                'unique_artists': stats['unique_artists'] or 0,
                'top_artist': top_artist['name'] if top_artist else None,
                'top_song': top_song['title'] if top_song else None,
                'peak_hour': top_hour['hour'] if top_hour else None
            })

        conn.close()

        return jsonify({
            'user1': users_data[0],
            'user2': users_data[1],
            'days': days
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats/heatmap')
def get_stats_heatmap():
    """Obtiene datos para el heatmap de actividad (hora x dia de semana)"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 500

    days = request.args.get('days', 30, type=int)
    days = min(days, 365)
    guild_id = request.args.get('guild_id', type=int)

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Obtener plays agrupados por hora y dia de la semana
        if guild_id:
            cursor.execute('''
                SELECT
                    CAST(strftime('%w', played_at) AS INTEGER) as dow,
                    CAST(strftime('%H', played_at) AS INTEGER) as hour,
                    COUNT(*) as plays
                FROM plays
                WHERE played_at >= DATE('now', ?) AND guild_id = ?
                GROUP BY dow, hour
            ''', (f'-{days} days', guild_id))
        else:
            cursor.execute('''
                SELECT
                    CAST(strftime('%w', played_at) AS INTEGER) as dow,
                    CAST(strftime('%H', played_at) AS INTEGER) as hour,
                    COUNT(*) as plays
                FROM plays
                WHERE played_at >= DATE('now', ?)
                GROUP BY dow, hour
            ''', (f'-{days} days',))
        rows = cursor.fetchall()
        conn.close()

        # Crear matriz 7x24 (dias x horas)
        # Inicializar con ceros
        matrix = [[0 for _ in range(24)] for _ in range(7)]

        max_value = 0
        for row in rows:
            dow = row['dow']  # 0=Sunday, 1=Monday...
            hour = row['hour']
            plays = row['plays']
            matrix[dow][hour] = plays
            if plays > max_value:
                max_value = plays

        # Reordenar para que empiece en Lunes (indice 1 -> 0)
        # Original: [Dom, Lun, Mar, Mie, Jue, Vie, Sab]
        # Nuevo: [Lun, Mar, Mie, Jue, Vie, Sab, Dom]
        reordered = matrix[1:] + [matrix[0]]

        return jsonify({
            'matrix': reordered,
            'max_value': max_value,
            'days': ['Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab', 'Dom'],
            'hours': [f'{h:02d}' for h in range(24)]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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
