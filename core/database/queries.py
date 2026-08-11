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
    ENTHUSIAST_MIN_PLAYS,
    WEEKEND_WARRIOR_THRESHOLD,
    COMMUTE_COMPANION_THRESHOLD,
    STUDY_BUDDY_MIN_SESSIONS,
    STUDY_BUDDY_AVG_DURATION,
    HIPSTER_DISCOVERY_DAYS
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
                   duration: Optional[int], listeners: List[Tuple[int, str, str]],
                   thumbnail_url: str = None, guild_icon_url: str = None,
                   requester_avatar_url: str = None):
    """
    Registra un evento de reproducción con todos los datos relacionados.
    Este es el punto de entrada principal para registrar reproducciones en el esquema v2.
    """
    conn = get_connection()

    try:
        # Obtener o crear todas las entidades
        guild_id = get_or_create_guild(guild_discord_id, guild_name, guild_icon_url, conn)
        requester_id = get_or_create_user(requester_discord_id, requester_name,
                                          avatar_url=requester_avatar_url, conn=conn)

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
        for listener_data in listeners:
            listener_discord_id, listener_name = listener_data[0], listener_data[1]
            listener_avatar_url = listener_data[2] if len(listener_data) > 2 else None
            listener_id = get_or_create_user(listener_discord_id, listener_name,
                                             avatar_url=listener_avatar_url, conn=conn)
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

    # Cerrar conexión antes de llamar a get_listening_patterns (que abre su propia conexión)
    conn.close()

    # Obtener patrones de escucha para personalidades expandidas
    patterns = get_listening_patterns(discord_user_id, discord_guild_id, year)

    # Calcular personalidad de escucha
    personality = _calculate_listening_personality(
        unique_tracks=basic_row['unique_tracks'],
        unique_artists=basic_row['unique_artists'],
        total_plays=basic_row['total_plays'],
        favorite_hour=favorite_hour,
        favorite_hour_plays=favorite_hour_plays,
        top_artist_plays=top_artists[0]['play_count'] if top_artists else 0,
        patterns=patterns
    )

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
                                     top_artist_plays: int,
                                     patterns: Dict[str, Any] = None) -> str:
    """
    Calcula una personalidad de escucha basada en los hábitos de escucha.

    Args:
        unique_tracks: Canciones únicas escuchadas
        unique_artists: Artistas únicos escuchados
        total_plays: Total de reproducciones
        favorite_hour: Hora favorita (0-23)
        favorite_hour_plays: Reproducciones en la hora favorita
        top_artist_plays: Reproducciones del artista #1
        patterns: Patrones de escucha de get_listening_patterns() (opcional)

    Returns:
        Nombre de personalidad (16 posibles)
    """
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

    # === NUEVAS PERSONALIDADES (prioridad alta) ===
    if patterns:
        # Weekend Warrior - escucha principalmente en fines de semana
        weekend_ratio = patterns['weekend_plays'] / total_plays if total_plays > 0 else 0
        if weekend_ratio > WEEKEND_WARRIOR_THRESHOLD and patterns['weekend_plays'] >= 50:
            return "Weekend Warrior"

        # Commute Companion - picos en horarios de tránsito (7-9AM, 5-7PM)
        commute_ratio = patterns['commute_plays'] / total_plays if total_plays > 0 else 0
        if commute_ratio > COMMUTE_COMPANION_THRESHOLD and patterns['commute_plays'] >= 30:
            return "Commute Companion"

        # Study Buddy - sesiones largas continuas (>2h)
        if patterns['study_sessions'] >= STUDY_BUDDY_MIN_SESSIONS and patterns['avg_session_duration'] > STUDY_BUDDY_AVG_DURATION:
            return "Study Buddy"

    # === PERSONALIDADES EXISTENTES (prioridad original) ===

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

    # Determinar personalidad (orden de prioridad)
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


# ============================================
# WRAPPED - QUERIES AVANZADAS
# ============================================

def get_user_monthly_breakdown(discord_user_id: int, discord_guild_id: int,
                                year: int) -> List[Dict[str, Any]]:
    """
    Obtiene estadísticas mes a mes para un usuario en un año.

    Returns: Lista de diccionarios, uno por mes (1-12) con:
        - month: int (1-12)
        - plays_count: int
        - time_seconds: int
        - unique_tracks: int
        - unique_artists: int
        - top_track: Dict[title, artist, play_count]
        - top_artist: Dict[name, play_count]
        - new_artists: int (artistas descubiertos este mes)
        - busiest_day_plays: int (máximo de plays en un día del mes)
    """
    conn = get_connection()
    cursor = conn.cursor()

    user_id = get_user_id_from_discord(discord_user_id, conn)
    guild_id = get_guild_id_from_discord(discord_guild_id, conn)

    if not user_id or not guild_id:
        conn.close()
        return []

    monthly_stats = []

    for month in range(1, 13):
        # Stats básicas del mes
        cursor.execute('''
            SELECT
                COUNT(*) as plays_count,
                COALESCE(SUM(t.duration_seconds), 0) as time_seconds,
                COUNT(DISTINCT p.track_id) as unique_tracks,
                COUNT(DISTINCT t.artist_id) as unique_artists
            FROM plays p
            JOIN tracks t ON p.track_id = t.id
            WHERE p.requester_id = ? AND p.guild_id = ? AND p.year = ? AND p.month = ?
        ''', (user_id, guild_id, year, month))

        basic_stats = cursor.fetchone()

        if basic_stats['plays_count'] == 0:
            continue  # Saltar meses sin actividad

        # Top canción del mes
        cursor.execute('''
            SELECT t.title, a.name as artist, COUNT(*) as play_count
            FROM plays p
            JOIN tracks t ON p.track_id = t.id
            LEFT JOIN artists a ON t.artist_id = a.id
            WHERE p.requester_id = ? AND p.guild_id = ? AND p.year = ? AND p.month = ?
            GROUP BY p.track_id
            ORDER BY play_count DESC
            LIMIT 1
        ''', (user_id, guild_id, year, month))

        top_track_row = cursor.fetchone()
        top_track = {
            'title': top_track_row['title'],
            'artist': top_track_row['artist'],
            'play_count': top_track_row['play_count']
        } if top_track_row else None

        # Top artista del mes
        cursor.execute('''
            SELECT a.name, COUNT(*) as play_count
            FROM plays p
            JOIN tracks t ON p.track_id = t.id
            LEFT JOIN artists a ON t.artist_id = a.id
            WHERE p.requester_id = ? AND p.guild_id = ? AND p.year = ? AND p.month = ?
            GROUP BY t.artist_id
            ORDER BY play_count DESC
            LIMIT 1
        ''', (user_id, guild_id, year, month))

        top_artist_row = cursor.fetchone()
        top_artist = {
            'name': top_artist_row['name'],
            'play_count': top_artist_row['play_count']
        } if top_artist_row else None

        # Artistas nuevos este mes (primera vez escuchados)
        cursor.execute('''
            SELECT COUNT(DISTINCT t.artist_id) as new_artists
            FROM plays p
            JOIN tracks t ON p.track_id = t.id
            WHERE p.requester_id = ? AND p.guild_id = ? AND p.year = ? AND p.month = ?
            AND t.artist_id NOT IN (
                SELECT DISTINCT t2.artist_id
                FROM plays p2
                JOIN tracks t2 ON p2.track_id = t2.id
                WHERE p2.requester_id = ? AND p2.guild_id = ?
                AND (p2.year < ? OR (p2.year = ? AND p2.month < ?))
            )
        ''', (user_id, guild_id, year, month, user_id, guild_id, year, year, month))

        new_artists_row = cursor.fetchone()

        # Día más activo del mes (para detectar maratones)
        cursor.execute('''
            SELECT COUNT(*) as day_plays
            FROM plays p
            WHERE p.requester_id = ? AND p.guild_id = ? AND p.year = ? AND p.month = ?
            GROUP BY p.day
            ORDER BY day_plays DESC
            LIMIT 1
        ''', (user_id, guild_id, year, month))

        busiest_day_row = cursor.fetchone()

        monthly_stats.append({
            'month': month,
            'plays_count': basic_stats['plays_count'],
            'time_seconds': basic_stats['time_seconds'],
            'unique_tracks': basic_stats['unique_tracks'],
            'unique_artists': basic_stats['unique_artists'],
            'top_track': top_track,
            'top_artist': top_artist,
            'new_artists': new_artists_row['new_artists'] if new_artists_row else 0,
            'busiest_day_plays': busiest_day_row['day_plays'] if busiest_day_row else 0
        })

    conn.close()
    return monthly_stats


def get_server_rankings(discord_guild_id: int, year: int) -> List[Dict[str, Any]]:
    """
    Obtiene rankings de todos los usuarios del servidor para un año.

    Returns: Lista ordenada por total_time_seconds descendente con:
        - user_discord_id: int
        - username: str
        - total_plays: int
        - total_time_seconds: int
        - unique_tracks: int
        - rank: int (posición, 1-indexed)
        - percentile: float (top X%)
    """
    conn = get_connection()
    cursor = conn.cursor()

    guild_id = get_guild_id_from_discord(discord_guild_id, conn)
    if not guild_id:
        conn.close()
        return []

    cursor.execute('''
        SELECT
            u.discord_id as user_discord_id,
            u.username,
            COUNT(*) as total_plays,
            COALESCE(SUM(t.duration_seconds), 0) as total_time_seconds,
            COUNT(DISTINCT p.track_id) as unique_tracks
        FROM plays p
        JOIN users u ON p.requester_id = u.id
        JOIN tracks t ON p.track_id = t.id
        WHERE p.guild_id = ? AND p.year = ?
        GROUP BY p.requester_id
        ORDER BY total_time_seconds DESC
    ''', (guild_id, year))

    users = cursor.fetchall()
    conn.close()

    total_users = len(users)
    rankings = []

    for rank, user in enumerate(users, start=1):
        percentile = (rank / total_users) if total_users > 0 else 1.0
        rankings.append({
            'user_discord_id': user['user_discord_id'],
            'username': user['username'],
            'total_plays': user['total_plays'],
            'total_time_seconds': user['total_time_seconds'],
            'unique_tracks': user['unique_tracks'],
            'rank': rank,
            'percentile': percentile
        })

    return rankings


def get_user_rank_in_server(discord_user_id: int, discord_guild_id: int,
                             year: int) -> Dict[str, Any]:
    """
    Obtiene la posición del usuario en el servidor.

    Returns:
        - rank: int (posición, ej: 3)
        - total_users: int (ej: 25)
        - percentile: float (ej: 0.12 = top 12%)
        - user_total_time: int
        - server_avg_time: float
        - comparison_ratio: float (ej: 2.5 = 2.5x más que promedio)
    """
    rankings = get_server_rankings(discord_guild_id, year)

    if not rankings:
        return {
            'rank': 0,
            'total_users': 0,
            'percentile': 1.0,
            'user_total_time': 0,
            'server_avg_time': 0,
            'comparison_ratio': 0
        }

    # Buscar usuario en rankings
    user_rank_data = None
    for ranking in rankings:
        if ranking['user_discord_id'] == discord_user_id:
            user_rank_data = ranking
            break

    if not user_rank_data:
        return {
            'rank': 0,
            'total_users': len(rankings),
            'percentile': 1.0,
            'user_total_time': 0,
            'server_avg_time': 0,
            'comparison_ratio': 0
        }

    # Calcular promedio del servidor
    total_time = sum(r['total_time_seconds'] for r in rankings)
    server_avg_time = total_time / len(rankings) if rankings else 0

    # Ratio de comparación
    comparison_ratio = (user_rank_data['total_time_seconds'] / server_avg_time) if server_avg_time > 0 else 0

    return {
        'rank': user_rank_data['rank'],
        'total_users': len(rankings),
        'percentile': user_rank_data['percentile'],
        'user_total_time': user_rank_data['total_time_seconds'],
        'server_avg_time': server_avg_time,
        'comparison_ratio': comparison_ratio
    }


def get_unique_songs_for_user(discord_user_id: int, discord_guild_id: int,
                               year: int) -> List[Dict[str, Any]]:
    """
    Canciones que SOLO este usuario escuchó en el servidor.

    Returns: Lista de:
        - track_title: str
        - artist_name: str
        - play_count: int (por este usuario)
        - first_played: datetime
    """
    conn = get_connection()
    cursor = conn.cursor()

    user_id = get_user_id_from_discord(discord_user_id, conn)
    guild_id = get_guild_id_from_discord(discord_guild_id, conn)

    if not user_id or not guild_id:
        conn.close()
        return []

    # Canciones que solo este usuario reprodujo
    cursor.execute('''
        SELECT
            t.title as track_title,
            a.name as artist_name,
            COUNT(*) as play_count,
            MIN(p.played_at) as first_played
        FROM plays p
        JOIN tracks t ON p.track_id = t.id
        LEFT JOIN artists a ON t.artist_id = a.id
        WHERE p.requester_id = ? AND p.guild_id = ? AND p.year = ?
        AND p.track_id NOT IN (
            SELECT DISTINCT track_id
            FROM plays
            WHERE guild_id = ? AND year = ? AND requester_id != ?
        )
        GROUP BY p.track_id
        ORDER BY play_count DESC
    ''', (user_id, guild_id, year, guild_id, year, user_id))

    results = []
    for row in cursor.fetchall():
        results.append({
            'track_title': row['track_title'],
            'artist_name': row['artist_name'],
            'play_count': row['play_count'],
            'first_played': row['first_played']
        })

    conn.close()
    return results


def get_user_records(discord_user_id: int, discord_guild_id: int,
                     year: int) -> Dict[str, Any]:
    """
    Récords personales del usuario.

    Returns:
        - busiest_day: Dict[date, plays_count, time_seconds]
        - longest_track: Dict[title, artist, duration]
        - shortest_track: Dict[title, artist, duration]
        - most_played_in_one_day: Dict[track_title, artist, count, date]
    """
    conn = get_connection()
    cursor = conn.cursor()

    user_id = get_user_id_from_discord(discord_user_id, conn)
    guild_id = get_guild_id_from_discord(discord_guild_id, conn)

    if not user_id or not guild_id:
        conn.close()
        return {}

    # Día más activo
    cursor.execute('''
        SELECT
            date_key as date,
            COUNT(*) as plays_count,
            COALESCE(SUM(t.duration_seconds), 0) as time_seconds
        FROM plays p
        JOIN tracks t ON p.track_id = t.id
        WHERE p.requester_id = ? AND p.guild_id = ? AND p.year = ?
        GROUP BY date_key
        ORDER BY plays_count DESC
        LIMIT 1
    ''', (user_id, guild_id, year))

    busiest_day = cursor.fetchone()

    # Canción más larga escuchada
    cursor.execute('''
        SELECT DISTINCT t.title, a.name as artist, t.duration_seconds as duration
        FROM plays p
        JOIN tracks t ON p.track_id = t.id
        LEFT JOIN artists a ON t.artist_id = a.id
        WHERE p.requester_id = ? AND p.guild_id = ? AND p.year = ?
        ORDER BY t.duration_seconds DESC
        LIMIT 1
    ''', (user_id, guild_id, year))

    longest_track = cursor.fetchone()

    # Canción más corta escuchada
    cursor.execute('''
        SELECT DISTINCT t.title, a.name as artist, t.duration_seconds as duration
        FROM plays p
        JOIN tracks t ON p.track_id = t.id
        LEFT JOIN artists a ON t.artist_id = a.id
        WHERE p.requester_id = ? AND p.guild_id = ? AND p.year = ? AND t.duration_seconds > 0
        ORDER BY t.duration_seconds ASC
        LIMIT 1
    ''', (user_id, guild_id, year))

    shortest_track = cursor.fetchone()

    # Canción más reproducida en un solo día
    cursor.execute('''
        SELECT
            t.title as track_title,
            a.name as artist,
            COUNT(*) as count,
            p.date_key as date
        FROM plays p
        JOIN tracks t ON p.track_id = t.id
        LEFT JOIN artists a ON t.artist_id = a.id
        WHERE p.requester_id = ? AND p.guild_id = ? AND p.year = ?
        GROUP BY p.track_id, p.date_key
        ORDER BY count DESC
        LIMIT 1
    ''', (user_id, guild_id, year))

    most_played_in_day = cursor.fetchone()

    conn.close()

    return {
        'busiest_day': {
            'date': busiest_day['date'],
            'plays_count': busiest_day['plays_count'],
            'time_seconds': busiest_day['time_seconds']
        } if busiest_day else None,
        'longest_track': {
            'title': longest_track['title'],
            'artist': longest_track['artist'],
            'duration': longest_track['duration']
        } if longest_track else None,
        'shortest_track': {
            'title': shortest_track['title'],
            'artist': shortest_track['artist'],
            'duration': shortest_track['duration']
        } if shortest_track else None,
        'most_played_in_one_day': {
            'track_title': most_played_in_day['track_title'],
            'artist': most_played_in_day['artist'],
            'count': most_played_in_day['count'],
            'date': most_played_in_day['date']
        } if most_played_in_day else None
    }


def get_listening_activity_heatmap(discord_user_id: int, discord_guild_id: int,
                                    year: int) -> Dict[int, Dict[int, int]]:
    """
    Mapa de calor de actividad por día de semana y hora.

    Returns: Dict de {day_of_week: {hour: play_count}}
    Ejemplo: {0: {8: 5, 9: 12, ...}, 1: {8: 3, ...}, ...}
    """
    conn = get_connection()
    cursor = conn.cursor()

    user_id = get_user_id_from_discord(discord_user_id, conn)
    guild_id = get_guild_id_from_discord(discord_guild_id, conn)

    if not user_id or not guild_id:
        conn.close()
        return {}

    cursor.execute('''
        SELECT day_of_week, hour, COUNT(*) as play_count
        FROM plays
        WHERE requester_id = ? AND guild_id = ? AND year = ?
        GROUP BY day_of_week, hour
        ORDER BY day_of_week, hour
    ''', (user_id, guild_id, year))

    heatmap = {}
    for row in cursor.fetchall():
        day = row['day_of_week']
        hour = row['hour']
        count = row['play_count']

        if day not in heatmap:
            heatmap[day] = {}
        heatmap[day][hour] = count

    conn.close()
    return heatmap


def get_artist_discovery_timeline(discord_user_id: int, discord_guild_id: int,
                                   year: int) -> List[Dict[str, Any]]:
    """
    Timeline de artistas descubiertos (primera vez escuchado).

    Returns: Lista ordenada por fecha de descubrimiento:
        - artist_name: str
        - discovered_date: str (YYYY-MM-DD)
        - month: int
        - total_plays_after_discovery: int
    """
    conn = get_connection()
    cursor = conn.cursor()

    user_id = get_user_id_from_discord(discord_user_id, conn)
    guild_id = get_guild_id_from_discord(discord_guild_id, conn)

    if not user_id or not guild_id:
        conn.close()
        return []

    cursor.execute('''
        SELECT
            a.name as artist_name,
            MIN(p.date_key) as discovered_date,
            MIN(p.month) as month,
            COUNT(*) as total_plays
        FROM plays p
        JOIN tracks t ON p.track_id = t.id
        LEFT JOIN artists a ON t.artist_id = a.id
        WHERE p.requester_id = ? AND p.guild_id = ? AND p.year = ?
        GROUP BY t.artist_id
        HAVING MIN(p.date_key) IS NOT NULL
        ORDER BY discovered_date
    ''', (user_id, guild_id, year))

    timeline = []
    for row in cursor.fetchall():
        timeline.append({
            'artist_name': row['artist_name'],
            'discovered_date': row['discovered_date'],
            'month': row['month'],
            'total_plays_after_discovery': row['total_plays']
        })

    conn.close()
    return timeline


def get_user_listening_evolution(discord_user_id: int, discord_guild_id: int,
                                  year: int) -> List[Dict[str, Any]]:
    """
    Evolución de estadísticas mes a mes para gráficos.

    Returns: Lista de 12 meses con:
        - month: int (1-12)
        - total_plays: int
        - total_hours: float
        - unique_artists: int
    """
    conn = get_connection()
    cursor = conn.cursor()

    user_id = get_user_id_from_discord(discord_user_id, conn)
    guild_id = get_guild_id_from_discord(discord_guild_id, conn)

    if not user_id or not guild_id:
        conn.close()
        return []

    evolution = []
    for month in range(1, 13):
        cursor.execute('''
            SELECT
                COUNT(*) as total_plays,
                COALESCE(SUM(t.duration_seconds), 0) / 3600.0 as total_hours,
                COUNT(DISTINCT t.artist_id) as unique_artists
            FROM plays p
            JOIN tracks t ON p.track_id = t.id
            WHERE p.requester_id = ? AND p.guild_id = ? AND p.year = ? AND p.month = ?
        ''', (user_id, guild_id, year, month))

        row = cursor.fetchone()
        evolution.append({
            'month': month,
            'total_plays': row['total_plays'] if row else 0,
            'total_hours': row['total_hours'] if row else 0,
            'unique_artists': row['unique_artists'] if row else 0
        })

    conn.close()
    return evolution


def get_top_artist_growth(discord_user_id: int, discord_guild_id: int,
                          current_year: int, previous_year: int) -> Dict[str, Any]:
    """
    Compara crecimiento del artista #1 entre años.

    Returns:
        - artist_name: str
        - current_year_plays: int
        - previous_year_plays: int
        - growth_percentage: float (ej: 340.5 = 340.5% crecimiento)
    """
    conn = get_connection()
    cursor = conn.cursor()

    user_id = get_user_id_from_discord(discord_user_id, conn)
    guild_id = get_guild_id_from_discord(discord_guild_id, conn)

    if not user_id or not guild_id:
        conn.close()
        return {}

    # Top artista del año actual
    cursor.execute('''
        SELECT a.name as artist_name, COUNT(*) as play_count
        FROM plays p
        JOIN tracks t ON p.track_id = t.id
        LEFT JOIN artists a ON t.artist_id = a.id
        WHERE p.requester_id = ? AND p.guild_id = ? AND p.year = ?
        GROUP BY t.artist_id
        ORDER BY play_count DESC
        LIMIT 1
    ''', (user_id, guild_id, current_year))

    current_top = cursor.fetchone()
    if not current_top:
        conn.close()
        return {}

    artist_name = current_top['artist_name']
    current_plays = current_top['play_count']

    # Plays del mismo artista en el año anterior
    cursor.execute('''
        SELECT COUNT(*) as play_count
        FROM plays p
        JOIN tracks t ON p.track_id = t.id
        LEFT JOIN artists a ON t.artist_id = a.id
        WHERE p.requester_id = ? AND p.guild_id = ? AND p.year = ? AND a.name = ?
    ''', (user_id, guild_id, previous_year, artist_name))

    previous_row = cursor.fetchone()
    previous_plays = previous_row['play_count'] if previous_row else 0

    # Calcular crecimiento
    if previous_plays > 0:
        growth_percentage = ((current_plays - previous_plays) / previous_plays) * 100
    else:
        growth_percentage = 100.0 if current_plays > 0 else 0

    conn.close()

    return {
        'artist_name': artist_name,
        'current_year_plays': current_plays,
        'previous_year_plays': previous_plays,
        'growth_percentage': growth_percentage
    }


def get_favorite_changes(discord_user_id: int, discord_guild_id: int,
                         year: int) -> int:
    """
    Cantidad de veces que cambió la canción favorita durante el año.

    Returns: int (número de cambios)
    """
    conn = get_connection()
    cursor = conn.cursor()

    user_id = get_user_id_from_discord(discord_user_id, conn)
    guild_id = get_guild_id_from_discord(discord_guild_id, conn)

    if not user_id or not guild_id:
        conn.close()
        return 0

    # Obtener top canción por mes
    top_tracks_by_month = []
    for month in range(1, 13):
        cursor.execute('''
            SELECT p.track_id
            FROM plays p
            WHERE p.requester_id = ? AND p.guild_id = ? AND p.year = ? AND p.month = ?
            GROUP BY p.track_id
            ORDER BY COUNT(*) DESC
            LIMIT 1
        ''', (user_id, guild_id, year, month))

        row = cursor.fetchone()
        if row:
            top_tracks_by_month.append(row['track_id'])

    conn.close()

    # Contar cambios (cuando el favorito de un mes es diferente al anterior)
    changes = 0
    for i in range(1, len(top_tracks_by_month)):
        if top_tracks_by_month[i] != top_tracks_by_month[i - 1]:
            changes += 1

    return changes


def get_listening_patterns(discord_user_id: int, discord_guild_id: int,
                           year: int) -> Dict[str, Any]:
    """
    Patrones de escucha para personalidades expandidas.

    Returns:
        - weekend_plays: int (reproducciones sáb-dom)
        - weekday_plays: int (reproducciones lun-vie)
        - commute_plays: int (7-9AM y 5-7PM)
        - study_sessions: int (sesiones >2h continuas)
        - avg_session_duration: float (segundos)
    """
    conn = get_connection()
    cursor = conn.cursor()

    user_id = get_user_id_from_discord(discord_user_id, conn)
    guild_id = get_guild_id_from_discord(discord_guild_id, conn)

    if not user_id or not guild_id:
        conn.close()
        return {
            'weekend_plays': 0,
            'weekday_plays': 0,
            'commute_plays': 0,
            'study_sessions': 0,
            'avg_session_duration': 0
        }

    # Weekend plays (sábado=6, domingo=0)
    cursor.execute('''
        SELECT COUNT(*) as count
        FROM plays
        WHERE requester_id = ? AND guild_id = ? AND year = ?
        AND (day_of_week = 0 OR day_of_week = 6)
    ''', (user_id, guild_id, year))

    weekend_plays = cursor.fetchone()['count']

    # Weekday plays (lun-vie = 1-5)
    cursor.execute('''
        SELECT COUNT(*) as count
        FROM plays
        WHERE requester_id = ? AND guild_id = ? AND year = ?
        AND day_of_week BETWEEN 1 AND 5
    ''', (user_id, guild_id, year))

    weekday_plays = cursor.fetchone()['count']

    # Commute hours (7-9AM y 5-7PM = 7, 8, 17, 18)
    cursor.execute('''
        SELECT COUNT(*) as count
        FROM plays
        WHERE requester_id = ? AND guild_id = ? AND year = ?
        AND hour IN (7, 8, 17, 18)
    ''', (user_id, guild_id, year))

    commute_plays = cursor.fetchone()['count']

    # Study sessions y avg duration (simplificado - contar sesiones por día)
    cursor.execute('''
        SELECT date_key, COUNT(*) as plays, SUM(t.duration_seconds) as total_duration
        FROM plays p
        JOIN tracks t ON p.track_id = t.id
        WHERE p.requester_id = ? AND p.guild_id = ? AND p.year = ?
        GROUP BY date_key
    ''', (user_id, guild_id, year))

    study_sessions = 0
    total_duration = 0
    session_count = 0

    for row in cursor.fetchall():
        session_duration = row['total_duration']
        total_duration += session_duration
        session_count += 1

        # Sesión de estudio: >2 horas continuas en un día
        if session_duration > 7200:  # 2 horas
            study_sessions += 1

    avg_session_duration = total_duration / session_count if session_count > 0 else 0

    conn.close()

    return {
        'weekend_plays': weekend_plays,
        'weekday_plays': weekday_plays,
        'commute_plays': commute_plays,
        'study_sessions': study_sessions,
        'avg_session_duration': avg_session_duration
    }


def compare_users_wrapped(discord_user_id_1: int, discord_user_id_2: int,
                          discord_guild_id: int, year: int) -> Dict[str, Any]:
    """
    Compara estadísticas de dos usuarios para Wrapped Battle.

    Returns:
        - user1: Dict[stats completas]
        - user2: Dict[stats completas]
        - categories: Dict[nombre_categoria: Dict[winner_id, user1_value, user2_value]]
    """
    # Obtener stats de ambos usuarios
    stats1 = get_user_yearly_stats(discord_user_id_1, discord_guild_id, year)
    stats2 = get_user_yearly_stats(discord_user_id_2, discord_guild_id, year)

    if not stats1 or not stats2:
        return {}

    # Comparar categorías
    categories = {}

    # 1. Tiempo total
    categories['time'] = {
        'winner_id': discord_user_id_1 if stats1['total_time_seconds'] > stats2['total_time_seconds'] else discord_user_id_2,
        'user1_value': stats1['total_time_seconds'],
        'user2_value': stats2['total_time_seconds']
    }

    # 2. Variedad (canciones únicas)
    categories['variety'] = {
        'winner_id': discord_user_id_1 if stats1['unique_tracks'] > stats2['unique_tracks'] else discord_user_id_2,
        'user1_value': stats1['unique_tracks'],
        'user2_value': stats2['unique_tracks']
    }

    # 3. Exploración (artistas únicos)
    categories['exploration'] = {
        'winner_id': discord_user_id_1 if stats1['unique_artists'] > stats2['unique_artists'] else discord_user_id_2,
        'user1_value': stats1['unique_artists'],
        'user2_value': stats2['unique_artists']
    }

    # 4. Lealtad (plays del top artista)
    user1_loyalty = stats1['top_artists'][0]['play_count'] if stats1.get('top_artists') else 0
    user2_loyalty = stats2['top_artists'][0]['play_count'] if stats2.get('top_artists') else 0

    categories['loyalty'] = {
        'winner_id': discord_user_id_1 if user1_loyalty > user2_loyalty else discord_user_id_2,
        'user1_value': user1_loyalty,
        'user2_value': user2_loyalty
    }

    # 5. Racha más larga
    categories['streak'] = {
        'winner_id': discord_user_id_1 if stats1.get('longest_streak', 0) > stats2.get('longest_streak', 0) else discord_user_id_2,
        'user1_value': stats1.get('longest_streak', 0),
        'user2_value': stats2.get('longest_streak', 0)
    }

    return {
        'user1': stats1,
        'user2': stats2,
        'categories': categories
    }
