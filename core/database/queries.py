"""
Consultas de base de datos optimizadas para el bot
Funciones de consulta centralizadas para el esquema v2
"""
import sqlite3
import re
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Dict, Any

from .schema import get_connection
from core.config import (
    PERSONALITY_MIN_HOUR_PLAYS,
    PERSONALITY_MIN_HOUR_PERCENTAGE,
    DEVOTED_FAN_THRESHOLD,
    EXPLORER_THRESHOLD,
    LOYALIST_THRESHOLD,
    SPECIALIST_MAX_ARTISTS,
    ENTHUSIAST_MIN_PLAYS
)


def normalize_string(s: str) -> str:
    """Normaliza una cadena para comparación (minúsculas, elimina espacios extra)"""
    if not s:
        return ""
    return re.sub(r'\s+', ' ', s.lower().strip())


def extract_youtube_id(url: str) -> Optional[str]:
    """Extrae el ID de video de YouTube de una URL"""
    if not url:
        return None
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


# ============================================
# GET O CREATE
# ============================================

def get_or_create_user(discord_id: int, username: str, display_name: str = None,
                       avatar_url: str = None, conn: sqlite3.Connection = None) -> int:
    """Obtiene el ID de usuario existente o crea uno nuevo, devuelve el ID de usuario interno"""
    should_close = conn is None
    if conn is None:
        conn = get_connection()
    cursor = conn.cursor()

    # Intentar encontrar usuario existente
    cursor.execute('SELECT id FROM users WHERE discord_id = ?', (discord_id,))
    row = cursor.fetchone()

    if row:
        # Actualizar username/display_name si ha cambiado
        cursor.execute('''
            UPDATE users
            SET username = ?, display_name = ?, avatar_url = COALESCE(?, avatar_url), updated_at = CURRENT_TIMESTAMP
            WHERE discord_id = ?
        ''', (username, display_name or username, avatar_url, discord_id))
        user_id = row['id']
    else:
        # Crear nuevo usuario
        cursor.execute('''
            INSERT INTO users (discord_id, username, display_name, avatar_url)
            VALUES (?, ?, ?, ?)
        ''', (discord_id, username, display_name or username, avatar_url))
        user_id = cursor.lastrowid

    conn.commit()
    if should_close:
        conn.close()
    return user_id


def get_or_create_guild(discord_id: int, name: str, icon_url: str = None,
                        conn: sqlite3.Connection = None) -> int:
    """Obtiene el Guild Id existente o crea uno nuevo, devuelve el Guild Id interno"""
    should_close = conn is None
    if conn is None:
        conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT id FROM guilds WHERE discord_id = ?', (discord_id,))
    row = cursor.fetchone()

    if row:
        cursor.execute('''
            UPDATE guilds
            SET name = ?, icon_url = COALESCE(?, icon_url), updated_at = CURRENT_TIMESTAMP
            WHERE discord_id = ?
        ''', (name, icon_url, discord_id))
        guild_id = row['id']
    else:
        cursor.execute('''
            INSERT INTO guilds (discord_id, name, icon_url)
            VALUES (?, ?, ?)
        ''', (discord_id, name, icon_url))
        guild_id = cursor.lastrowid

    conn.commit()
    if should_close:
        conn.close()
    return guild_id


def get_or_create_artist(name: str, image_url: str = None, spotify_id: str = None,
                         conn: sqlite3.Connection = None) -> int:
    """Obtiene el ID de artista existente o crea uno nuevo"""
    if not name:
        return None

    should_close = conn is None
    if conn is None:
        conn = get_connection()
    cursor = conn.cursor()

    name_normalized = normalize_string(name)

    cursor.execute('SELECT id FROM artists WHERE name_normalized = ?', (name_normalized,))
    row = cursor.fetchone()

    if row:
        # Actualizar información adicional si se proporciona
        if image_url or spotify_id:
            cursor.execute('''
                UPDATE artists
                SET image_url = COALESCE(?, image_url),
                    spotify_id = COALESCE(?, spotify_id)
                WHERE id = ?
            ''', (image_url, spotify_id, row['id']))
        artist_id = row['id']
    else:
        cursor.execute('''
            INSERT INTO artists (name, name_normalized, image_url, spotify_id)
            VALUES (?, ?, ?, ?)
        ''', (name, name_normalized, image_url, spotify_id))
        artist_id = cursor.lastrowid

    conn.commit()
    if should_close:
        conn.close()
    return artist_id


def get_or_create_track(title: str, artist_id: int = None, duration_seconds: int = None,
                        url: str = None, thumbnail_url: str = None, spotify_id: str = None,
                        conn: sqlite3.Connection = None) -> int:
    """Obtiene el ID de pista existente o crea una nueva pista"""
    should_close = conn is None
    if conn is None:
        conn = get_connection()
    cursor = conn.cursor()

    title_normalized = normalize_string(title)
    youtube_id = extract_youtube_id(url) if url else None

    # Intentar encontrar por YouTube ID primero (el más fiable)
    if youtube_id:
        cursor.execute('SELECT id FROM tracks WHERE youtube_id = ?', (youtube_id,))
        row = cursor.fetchone()
        if row:
            # Actualizar información adicional
            cursor.execute('''
                UPDATE tracks
                SET duration_seconds = COALESCE(?, duration_seconds),
                    thumbnail_url = COALESCE(?, thumbnail_url),
                    artist_id = COALESCE(?, artist_id)
                WHERE id = ?
            ''', (duration_seconds, thumbnail_url, artist_id, row['id']))
            conn.commit()
            # Añadir URL si no existe
            _add_track_url(row['id'], url, 'youtube', conn)
            if should_close:
                conn.close()
            return row['id']

    # Intentar encontrar por título + artista
    cursor.execute('''
        SELECT id FROM tracks
        WHERE title_normalized = ? AND (artist_id = ? OR (artist_id IS NULL AND ? IS NULL))
    ''', (title_normalized, artist_id, artist_id))
    row = cursor.fetchone()

    if row:
        # Actualizar pista con nueva información
        cursor.execute('''
            UPDATE tracks
            SET duration_seconds = COALESCE(?, duration_seconds),
                youtube_id = COALESCE(?, youtube_id),
                thumbnail_url = COALESCE(?, thumbnail_url),
                spotify_id = COALESCE(?, spotify_id)
            WHERE id = ?
        ''', (duration_seconds, youtube_id, thumbnail_url, spotify_id, row['id']))
        track_id = row['id']
    else:
        # Crear nueva pista
        cursor.execute('''
            INSERT INTO tracks (title, title_normalized, artist_id, duration_seconds, youtube_id, spotify_id, thumbnail_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (title, title_normalized, artist_id, duration_seconds, youtube_id, spotify_id, thumbnail_url))
        track_id = cursor.lastrowid

    conn.commit()

    # Añadir URL a track_urls
    if url:
        source = 'youtube' if 'youtube' in url or 'youtu.be' in url else 'other'
        _add_track_url(track_id, url, source, conn)

    if should_close:
        conn.close()
    return track_id


def _add_track_url(track_id: int, url: str, source: str, conn: sqlite3.Connection):
    """Añade una URL a la tabla track_urls si no existe"""
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO track_urls (track_id, url, source)
            VALUES (?, ?, ?)
        ''', (track_id, url, source))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # URL duplicada, omitir


# ============================================
# RECORD PLAY
# ============================================

def record_play(guild_discord_id: int, guild_name: str,
                   requester_discord_id: int, requester_name: str,
                   song_title: str, artist: Optional[str], url: Optional[str],
                   duration: Optional[int], listeners: List[Tuple[int, str]],
                   thumbnail_url: str = None, guild_icon_url: str = None):
    """
    Registra un evento de reproducción con todos los datos relacionados.
    Este es el punto de entrada principal para registrar reproducciones en el esquema v2.
    """
    conn = get_connection()

    try:
        # Obtener o crear todas las entidades
        guild_id = get_or_create_guild(guild_discord_id, guild_name, guild_icon_url, conn)
        requester_id = get_or_create_user(requester_discord_id, requester_name, conn=conn)

        artist_id = None
        if artist:
            artist_id = get_or_create_artist(artist, conn=conn)

        track_id = get_or_create_track(
            title=song_title,
            artist_id=artist_id,
            duration_seconds=duration,
            url=url,
            thumbnail_url=thumbnail_url,
            conn=conn
        )

        # Insertar registro de reproducción
        played_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO plays (guild_id, requester_id, track_id, url, played_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (guild_id, requester_id, track_id, url, played_at))
        play_id = cursor.lastrowid

        # Insertar oyentes
        for listener_discord_id, listener_name in listeners:
            listener_id = get_or_create_user(listener_discord_id, listener_name, conn=conn)
            try:
                cursor.execute('''
                    INSERT INTO listens (play_id, user_id)
                    VALUES (?, ?)
                ''', (play_id, listener_id))
            except sqlite3.IntegrityError:
                pass  # Oyente duplicado, omitir

        conn.commit()

        # Actualizar estadísticas diarias
        date_key = played_at[:10]  # 'YYYY-MM-DD'
        _update_daily_stats(requester_id, guild_id, date_key, duration or 0, track_id, artist_id, conn)

        # Actualizar racha
        update_user_streak(requester_id, guild_id, date_key, conn)

        conn.close()
        logging.debug(f"Reproducción registrada: {song_title} por {artist} para {len(listeners)} oyentes")

    except Exception as e:
        conn.rollback()
        conn.close()
        logging.error(f"Error al registrar reproducción: {e}")
        raise


def _update_daily_stats(user_id: int, guild_id: int, date_key: str,
                        duration: int, track_id: int, artist_id: int,
                        conn: sqlite3.Connection):
    """Actualiza o crea estadísticas diarias para un usuario"""
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO daily_stats_user (user_id, guild_id, date_key, plays_count, time_seconds, unique_tracks, unique_artists)
        VALUES (?, ?, ?, 1, ?, 1, ?)
        ON CONFLICT(user_id, guild_id, date_key) DO UPDATE SET
            plays_count = plays_count + 1,
            time_seconds = time_seconds + excluded.time_seconds
    ''', (user_id, guild_id, date_key, duration, 1 if artist_id else 0))

    conn.commit()


# ============================================
# ADMIN DE STREAKS
# ============================================

def get_user_streak(user_id: int, guild_id: int, conn: sqlite3.Connection = None) -> Dict[str, Any]:
    """Obtiene la información de racha actual del usuario"""
    should_close = conn is None
    if conn is None:
        conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT current_streak, longest_streak, last_listen_date, streak_start_date
        FROM user_streaks
        WHERE user_id = ? AND guild_id = ?
    ''', (user_id, guild_id))

    row = cursor.fetchone()
    if should_close:
        conn.close()

    if row:
        return {
            'current_streak': row['current_streak'],
            'longest_streak': row['longest_streak'],
            'last_listen_date': row['last_listen_date'],
            'streak_start_date': row['streak_start_date']
        }
    return {
        'current_streak': 0,
        'longest_streak': 0,
        'last_listen_date': None,
        'streak_start_date': None
    }


def update_user_streak(user_id: int, guild_id: int, date_key: str,
                       conn: sqlite3.Connection = None):
    """Actualiza la racha del usuario basada en una nueva reproducción"""
    should_close = conn is None
    if conn is None:
        conn = get_connection()
    cursor = conn.cursor()

    # Obtener información de la racha actual
    cursor.execute('''
        SELECT current_streak, longest_streak, last_listen_date, streak_start_date
        FROM user_streaks
        WHERE user_id = ? AND guild_id = ?
    ''', (user_id, guild_id))

    row = cursor.fetchone()

    today = datetime.strptime(date_key, '%Y-%m-%d').date()

    if row:
        last_date_str = row['last_listen_date']
        current_streak = row['current_streak']
        longest_streak = row['longest_streak']
        streak_start = row['streak_start_date']

        if last_date_str:
            last_date = datetime.strptime(last_date_str, '%Y-%m-%d').date()
            days_diff = (today - last_date).days

            if days_diff == 0:
                # Mismo día, no se necesita actualizar la racha
                if should_close:
                    conn.close()
                return
            elif days_diff == 1:
                # Día consecutivo, incrementar racha
                current_streak += 1
            else:
                # Racha rota, iniciar nueva
                current_streak = 1
                streak_start = date_key
        else:
            current_streak = 1
            streak_start = date_key

        longest_streak = max(longest_streak, current_streak)

        cursor.execute('''
            UPDATE user_streaks
            SET current_streak = ?, longest_streak = ?, last_listen_date = ?, streak_start_date = ?
            WHERE user_id = ? AND guild_id = ?
        ''', (current_streak, longest_streak, date_key, streak_start, user_id, guild_id))
    else:
        # Primera vez para el usuario
        cursor.execute('''
            INSERT INTO user_streaks (user_id, guild_id, current_streak, longest_streak, last_listen_date, streak_start_date)
            VALUES (?, ?, 1, 1, ?, ?)
        ''', (user_id, guild_id, date_key, date_key))

    conn.commit()
    if should_close:
        conn.close()


# ============================================
# QUERY FUNCTIONS
# ============================================

def get_user_id_from_discord(discord_id: int, conn: sqlite3.Connection = None) -> Optional[int]:
    """Obtiene el ID de usuario interno a partir del ID de Discord"""
    should_close = conn is None
    if conn is None:
        conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE discord_id = ?', (discord_id,))
    row = cursor.fetchone()
    if should_close:
        conn.close()
    return row['id'] if row else None


def get_guild_id_from_discord(discord_id: int, conn: sqlite3.Connection = None) -> Optional[int]:
    """Obtiene el Guild Id interno a partir del ID de Discord"""
    should_close = conn is None
    if conn is None:
        conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM guilds WHERE discord_id = ?', (discord_id,))
    row = cursor.fetchone()
    if should_close:
        conn.close()
    return row['id'] if row else None


def get_user_stats(discord_user_id: int, discord_guild_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Obtiene estadísticas de usuario.
    Devuelve: total_solicitado, total_escuchado, tiempo_total, primera_reproduccion, ultima_reproduccion
    """
    conn = get_connection()
    cursor = conn.cursor()

    user_id = get_user_id_from_discord(discord_user_id, conn)
    if not user_id:
        conn.close()
        return {
            'total_requested': 0,
            'total_listened': 0,
            'total_time': 0,
            'first_play': None,
            'last_play': None
        }

    guild_filter = ""
    params = [user_id]
    if discord_guild_id:
        guild_id = get_guild_id_from_discord(discord_guild_id, conn)
        if guild_id:
            guild_filter = "AND p.guild_id = ?"
            params.append(guild_id)

    # Contar reproducciones como solicitante
    cursor.execute(f'''
        SELECT COUNT(*) as total_requested
        FROM plays p
        WHERE p.requester_id = ? {guild_filter}
    ''', params)
    total_requested = cursor.fetchone()['total_requested']

    # Contar escuchas y tiempo total
    listen_params = [user_id]
    listen_guild_filter = ""
    if discord_guild_id:
        guild_id = get_guild_id_from_discord(discord_guild_id, conn)
        if guild_id:
            listen_guild_filter = "AND p.guild_id = ?"
            listen_params.append(guild_id)

    cursor.execute(f'''
        SELECT
            COUNT(*) as total_listened,
            COALESCE(SUM(t.duration_seconds), 0) as total_time,
            MIN(p.played_at) as first_play,
            MAX(p.played_at) as last_play
        FROM listens l
        JOIN plays p ON l.play_id = p.id
        JOIN tracks t ON p.track_id = t.id
        WHERE l.user_id = ? {listen_guild_filter}
    ''', listen_params)

    row = cursor.fetchone()
    conn.close()

    return {
        'total_requested': total_requested,
        'total_listened': row['total_listened'],
        'total_time': row['total_time'],
        'first_play': row['first_play'],
        'last_play': row['last_play']
    }


def get_user_top_songs(discord_user_id: int, discord_guild_id: Optional[int] = None,
                          limit: int = 10) -> List[Tuple[str, str, int]]:
    """
    Obtiene las canciones más solicitadas por un usuario.
    Devuelve: lista de (título_canción, artista, contador_solicitudes)
    """
    conn = get_connection()
    cursor = conn.cursor()

    user_id = get_user_id_from_discord(discord_user_id, conn)
    if not user_id:
        conn.close()
        return []

    guild_filter = ""
    params = [user_id]
    if discord_guild_id:
        guild_id = get_guild_id_from_discord(discord_guild_id, conn)
        if guild_id:
            guild_filter = "AND p.guild_id = ?"
            params.append(guild_id)

    params.append(limit)

    cursor.execute(f'''
        SELECT t.title, a.name as artist, COUNT(*) as request_count
        FROM plays p
        JOIN tracks t ON p.track_id = t.id
        LEFT JOIN artists a ON t.artist_id = a.id
        WHERE p.requester_id = ? {guild_filter}
        GROUP BY t.id
        ORDER BY request_count DESC
        LIMIT ?
    ''', params)

    results = [(row['title'], row['artist'], row['request_count']) for row in cursor.fetchall()]
    conn.close()
    return results


def get_user_top_artists(discord_user_id: int, discord_guild_id: Optional[int] = None,
                         limit: int = 10, year: int = None) -> List[Tuple[str, int, int]]:
    """
    Obtiene los artistas principales para un usuario.
    Devuelve: lista de (nombre_artista, contador_reproducciones, tiempo_total_segundos)
    """
    conn = get_connection()
    cursor = conn.cursor()

    user_id = get_user_id_from_discord(discord_user_id, conn)
    if not user_id:
        conn.close()
        return []

    filters = ["p.requester_id = ?", "a.id IS NOT NULL"]
    params = [user_id]

    if discord_guild_id:
        guild_id = get_guild_id_from_discord(discord_guild_id, conn)
        if guild_id:
            filters.append("p.guild_id = ?")
            params.append(guild_id)

    if year:
        filters.append("p.year = ?")
        params.append(year)

    params.append(limit)
    where_clause = " AND ".join(filters)

    cursor.execute(f'''
        SELECT a.name, COUNT(*) as play_count, COALESCE(SUM(t.duration_seconds), 0) as total_time
        FROM plays p
        JOIN tracks t ON p.track_id = t.id
        JOIN artists a ON t.artist_id = a.id
        WHERE {where_clause}
        GROUP BY a.id
        ORDER BY play_count DESC
        LIMIT ?
    ''', params)

    results = [(row['name'], row['play_count'], row['total_time']) for row in cursor.fetchall()]
    conn.close()
    return results


def get_server_top_songs(discord_guild_id: int, limit: int = 10) -> List[Tuple[str, str, int]]:
    """
    Obtiene las canciones principales en un servidor.
    Devuelve: lista de (título_canción, artista, contador_solicitudes)
    """
    conn = get_connection()
    cursor = conn.cursor()

    guild_id = get_guild_id_from_discord(discord_guild_id, conn)
    if not guild_id:
        conn.close()
        return []

    cursor.execute('''
        SELECT t.title, a.name as artist, COUNT(*) as request_count
        FROM plays p
        JOIN tracks t ON p.track_id = t.id
        LEFT JOIN artists a ON t.artist_id = a.id
        WHERE p.guild_id = ?
        GROUP BY t.id
        ORDER BY request_count DESC
        LIMIT ?
    ''', (guild_id, limit))

    results = [(row['title'], row['artist'], row['request_count']) for row in cursor.fetchall()]
    conn.close()
    return results


def get_server_top_users(discord_guild_id: int, limit: int = 10) -> List[Tuple[int, str, int, int]]:
    """
    Obtiene los usuarios principales en un servidor.
    Devuelve: lista de (discord_user_id, user_name, request_count, total_time)
    """
    conn = get_connection()
    cursor = conn.cursor()

    guild_id = get_guild_id_from_discord(discord_guild_id, conn)
    if not guild_id:
        conn.close()
        return []

    cursor.execute('''
        SELECT
            u.discord_id,
            u.display_name,
            COUNT(*) as request_count,
            COALESCE(SUM(t.duration_seconds), 0) as total_time
        FROM plays p
        JOIN users u ON p.requester_id = u.id
        JOIN tracks t ON p.track_id = t.id
        WHERE p.guild_id = ?
        GROUP BY u.id
        ORDER BY request_count DESC
        LIMIT ?
    ''', (guild_id, limit))

    results = [(row['discord_id'], row['display_name'], row['request_count'], row['total_time'])
               for row in cursor.fetchall()]
    conn.close()
    return results


def get_user_history(discord_user_id: int, discord_guild_id: Optional[int] = None,
                        limit: int = 20) -> List[Tuple[str, str, str]]:
    """
    Obtiene el historial de reproducción reciente de un usuario.
    Devuelve: lista de (título_canción, artista, reproducido_en)
    """
    conn = get_connection()
    cursor = conn.cursor()

    user_id = get_user_id_from_discord(discord_user_id, conn)
    if not user_id:
        conn.close()
        return []

    guild_filter = ""
    params = [user_id]
    if discord_guild_id:
        guild_id = get_guild_id_from_discord(discord_guild_id, conn)
        if guild_id:
            guild_filter = "AND p.guild_id = ?"
            params.append(guild_id)

    params.append(limit)

    cursor.execute(f'''
        SELECT t.title, a.name as artist, p.played_at
        FROM plays p
        JOIN tracks t ON p.track_id = t.id
        LEFT JOIN artists a ON t.artist_id = a.id
        WHERE p.requester_id = ? {guild_filter}
        ORDER BY p.played_at DESC
        LIMIT ?
    ''', params)

    results = [(row['title'], row['artist'], row['played_at']) for row in cursor.fetchall()]
    conn.close()
    return results


# ============================================
# QUERIES PARA WRAPPED
# ============================================

def get_user_yearly_stats(discord_user_id: int, discord_guild_id: int,
                          year: int) -> Dict[str, Any]:
    """Obtiene estadísticas anuales completas para un usuario (para Wrapped)"""
    conn = get_connection()
    cursor = conn.cursor()

    user_id = get_user_id_from_discord(discord_user_id, conn)
    guild_id = get_guild_id_from_discord(discord_guild_id, conn)

    if not user_id or not guild_id:
        conn.close()
        return None

    # Estadísticas básicas
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
        WHERE p.requester_id = ? AND p.guild_id = ? AND p.year = ?
    ''', (user_id, guild_id, year))

    basic_row = cursor.fetchone()

    if not basic_row or basic_row['total_plays'] == 0:
        conn.close()
        return None

    # Top 5 canciones
    cursor.execute('''
        SELECT t.title, a.name as artist, COUNT(*) as play_count, t.thumbnail_url
        FROM plays p
        JOIN tracks t ON p.track_id = t.id
        LEFT JOIN artists a ON t.artist_id = a.id
        WHERE p.requester_id = ? AND p.guild_id = ? AND p.year = ?
        GROUP BY t.id
        ORDER BY play_count DESC
        LIMIT 5
    ''', (user_id, guild_id, year))
    top_tracks = [dict(row) for row in cursor.fetchall()]

    # Top 5 artistas
    cursor.execute('''
        SELECT a.name, COUNT(*) as play_count, COALESCE(SUM(t.duration_seconds), 0) as total_time
        FROM plays p
        JOIN tracks t ON p.track_id = t.id
        JOIN artists a ON t.artist_id = a.id
        WHERE p.requester_id = ? AND p.guild_id = ? AND p.year = ?
        GROUP BY a.id
        ORDER BY play_count DESC
        LIMIT 5
    ''', (user_id, guild_id, year))
    top_artists = [dict(row) for row in cursor.fetchall()]

    # Hora favorita
    cursor.execute('''
        SELECT hour, COUNT(*) as count
        FROM plays
        WHERE requester_id = ? AND guild_id = ? AND year = ?
        GROUP BY hour
        ORDER BY count DESC
        LIMIT 1
    ''', (user_id, guild_id, year))
    hour_row = cursor.fetchone()
    favorite_hour = hour_row['hour'] if hour_row else None
    favorite_hour_plays = hour_row['count'] if hour_row else 0

    # Día favorito de la semana
    cursor.execute('''
        SELECT day_of_week, COUNT(*) as count
        FROM plays
        WHERE requester_id = ? AND guild_id = ? AND year = ?
        GROUP BY day_of_week
        ORDER BY count DESC
        LIMIT 1
    ''', (user_id, guild_id, year))
    day_row = cursor.fetchone()
    favorite_day = day_row['day_of_week'] if day_row else None

    # Primera canción del año
    cursor.execute('''
        SELECT t.title, a.name as artist, p.played_at
        FROM plays p
        JOIN tracks t ON p.track_id = t.id
        LEFT JOIN artists a ON t.artist_id = a.id
        WHERE p.requester_id = ? AND p.guild_id = ? AND p.year = ?
        ORDER BY p.played_at ASC
        LIMIT 1
    ''', (user_id, guild_id, year))
    first_track_row = cursor.fetchone()
    first_track = dict(first_track_row) if first_track_row else None

    # Obtener información de la racha
    streak_info = get_user_streak(user_id, guild_id, conn)

    # Calcular personalidad de escucha
    personality = _calculate_listening_personality(
        unique_tracks=basic_row['unique_tracks'],
        unique_artists=basic_row['unique_artists'],
        total_plays=basic_row['total_plays'],
        favorite_hour=favorite_hour,
        favorite_hour_plays=favorite_hour_plays,
        top_artist_plays=top_artists[0]['play_count'] if top_artists else 0
    )

    conn.close()

    return {
        'year': year,
        'total_plays': basic_row['total_plays'],
        'total_time_seconds': basic_row['total_time'],
        'unique_tracks': basic_row['unique_tracks'],
        'unique_artists': basic_row['unique_artists'],
        'first_play': basic_row['first_play'],
        'last_play': basic_row['last_play'],
        'top_tracks': top_tracks,
        'top_artists': top_artists,
        'favorite_hour': favorite_hour,
        'favorite_day_of_week': favorite_day,
        'first_track': first_track,
        'longest_streak': streak_info['longest_streak'],
        'current_streak': streak_info['current_streak'],
        'listening_personality': personality
    }


def get_user_listening_hours(discord_user_id: int, discord_guild_id: int,
                             year: int = None) -> Dict[int, int]:
    """Obtiene el recuento de reproducciones por hora para un usuario"""
    conn = get_connection()
    cursor = conn.cursor()

    user_id = get_user_id_from_discord(discord_user_id, conn)
    guild_id = get_guild_id_from_discord(discord_guild_id, conn)

    if not user_id or not guild_id:
        conn.close()
        return {}

    year_filter = ""
    params = [user_id, guild_id]
    if year:
        year_filter = "AND year = ?"
        params.append(year)

    cursor.execute(f'''
        SELECT hour, COUNT(*) as count
        FROM plays
        WHERE requester_id = ? AND guild_id = ? {year_filter}
        GROUP BY hour
        ORDER BY hour
    ''', params)

    results = {row['hour']: row['count'] for row in cursor.fetchall()}
    conn.close()
    return results


def get_user_listening_days(discord_user_id: int, discord_guild_id: int,
                            year: int = None) -> Dict[int, int]:
    """Obtiene el recuento de reproducciones por día de la semana para un usuario"""
    conn = get_connection()
    cursor = conn.cursor()

    user_id = get_user_id_from_discord(discord_user_id, conn)
    guild_id = get_guild_id_from_discord(discord_guild_id, conn)

    if not user_id or not guild_id:
        conn.close()
        return {}

    year_filter = ""
    params = [user_id, guild_id]
    if year:
        year_filter = "AND year = ?"
        params.append(year)

    cursor.execute(f'''
        SELECT day_of_week, COUNT(*) as count
        FROM plays
        WHERE requester_id = ? AND guild_id = ? {year_filter}
        GROUP BY day_of_week
        ORDER BY day_of_week
    ''', params)

    results = {row['day_of_week']: row['count'] for row in cursor.fetchall()}
    conn.close()
    return results


def _calculate_listening_personality(unique_tracks: int, unique_artists: int,
                                     total_plays: int, favorite_hour: int,
                                     favorite_hour_plays: int,
                                     top_artist_plays: int) -> str:
    """Calcula una personalidad de escucha basada en los hábitos de escucha"""
    if total_plays == 0:
        return "Newcomer"

    # Calcular proporciones
    variety_ratio = unique_tracks / total_plays if total_plays > 0 else 0
    artist_loyalty = top_artist_plays / total_plays if total_plays > 0 else 0
    hour_percentage = favorite_hour_plays / total_plays if total_plays > 0 else 0

    # Validar que la hora favorita sea significativa
    is_hour_significant = (
        favorite_hour_plays >= PERSONALITY_MIN_HOUR_PLAYS
        and hour_percentage >= PERSONALITY_MIN_HOUR_PERCENTAGE
    )

    # Comprobación de noctámbulo (18:00 - 4:00) - incluye "Noche" y "Madrugada"
    is_night_owl = (
        favorite_hour is not None
        and (favorite_hour >= 18 or favorite_hour <= 4)
        and is_hour_significant
    )

    # Comprobación de madrugador (5:00 - 11:00)
    is_early_bird = (
        favorite_hour is not None
        and 5 <= favorite_hour <= 11
        and is_hour_significant
    )

    # Determinar personalidad
    if artist_loyalty > DEVOTED_FAN_THRESHOLD:
        return "Devoted Fan"
    elif variety_ratio > EXPLORER_THRESHOLD:
        return "Explorer"
    elif variety_ratio < LOYALIST_THRESHOLD:
        return "Loyalist"
    elif is_night_owl:
        return "Night Owl"
    elif is_early_bird:
        return "Early Bird"
    elif unique_artists < SPECIALIST_MAX_ARTISTS:
        return "Specialist"
    elif total_plays > ENTHUSIAST_MIN_PLAYS:
        return "Music Enthusiast"
    else:
        return "Casual Listener"


# ============================================
# SERVER STATS
# ============================================

def get_server_stats(discord_guild_id: int) -> Dict[str, Any]:
    """
    Obtiene estadísticas generales del servidor.
    Devuelve: total_plays, total_time, unique_tracks, unique_artists, first_play, last_play
    """
    conn = get_connection()
    cursor = conn.cursor()

    guild_id = get_guild_id_from_discord(discord_guild_id, conn)
    if not guild_id:
        conn.close()
        return {
            'total_plays': 0,
            'total_time': 0,
            'unique_tracks': 0,
            'unique_artists': 0,
            'first_play': None,
            'last_play': None
        }

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
        WHERE p.guild_id = ?
    ''', (guild_id,))

    row = cursor.fetchone()
    conn.close()

    return {
        'total_plays': row['total_plays'],
        'total_time': row['total_time'],
        'unique_tracks': row['unique_tracks'],
        'unique_artists': row['unique_artists'],
        'first_play': row['first_play'],
        'last_play': row['last_play']
    }
