"""
Modulo para manejo de estadisticas de reproducciones con SQLite

Este modulo actua como facade para el nuevo sistema de base de datos,
manteniendo compatibilidad con los comandos existentes.
"""
import logging
from typing import Optional, List, Tuple, Dict, Any

from core.config import STATS_DATABASE_PATH
from core.database.schema import init_database_v2, get_connection, check_v1_tables_exist, get_schema_version
from core.database.migrations import migrate_from_v1, check_migration_needed
from core.database.queries import (
    record_play_v2,
    get_user_stats_v2,
    get_user_top_songs_v2,
    get_user_top_artists,
    get_server_top_songs_v2,
    get_server_top_users_v2,
    get_user_history_v2,
    get_user_yearly_stats,
    get_user_listening_hours,
    get_user_listening_days,
    get_user_streak,
    update_user_streak,
)


def _check_listens_schema_is_v2() -> bool:
    """Verifica si la tabla listens tiene la estructura v2 (play_id en vez de request_id)."""
    import sqlite3
    try:
        conn = sqlite3.connect(STATS_DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(listens)")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()
        return 'play_id' in columns
    except:
        return True  # Si no existe, asumimos que está bien


def init_database():
    """
    Inicializa la base de datos.
    Si existe una base de datos v1, la migra automáticamente a v2.
    """
    import os
    try:
        if os.path.exists(STATS_DATABASE_PATH):
            if not _check_listens_schema_is_v2():
                logging.info("Detectada tabla listens con estructura v1, forzando migración...")
                migrate_from_v1(force=True)
                logging.info("Base de datos migrada correctamente")
                return

        if check_migration_needed():
            logging.info("Migración de v1 a v2 detectada como necesaria, ejecutando...")
            migrate_from_v1()
        else:
            init_database_v2()

        logging.info("Base de datos inicializada correctamente")
    except Exception as e:
        logging.error(f"Error inicializando base de datos: {e}")
        try:
            init_database_v2()
        except Exception as e2:
            logging.error(f"Error en fallback de inicialización: {e2}")


def record_play(guild_id: int, requester_id: int, requester_name: str,
                song_title: str, artist: Optional[str], url: Optional[str],
                duration: Optional[int], listeners: List[Tuple[int, str]],
                guild_name: str = None, thumbnail_url: str = None,
                guild_icon_url: str = None):
    """
    Registra una reproduccion completa.
    API compatible con v1 pero usa el nuevo esquema v2.

    Args:
        guild_id: ID del servidor de Discord
        requester_id: ID del usuario que pidio la cancion
        requester_name: Nombre del usuario que pidio la cancion
        song_title: Titulo de la cancion
        artist: Artista (opcional)
        url: URL de la cancion (opcional)
        duration: Duracion en segundos (opcional)
        listeners: Lista de tuplas (user_id, user_name) de los oyentes
        guild_name: Nombre del servidor (opcional, para mejor tracking)
        thumbnail_url: URL del thumbnail (opcional)
        guild_icon_url: URL del icono del servidor (opcional)
    """
    try:
        if guild_name is None:
            guild_name = f"Server {guild_id}"

        record_play_v2(
            guild_discord_id=guild_id,
            guild_name=guild_name,
            requester_discord_id=requester_id,
            requester_name=requester_name,
            song_title=song_title,
            artist=artist,
            url=url,
            duration=duration,
            listeners=listeners,
            thumbnail_url=thumbnail_url,
            guild_icon_url=guild_icon_url
        )
    except Exception as e:
        logging.error(f"Error recording play: {e}")
        raise


def get_user_stats(user_id: int, guild_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Obtiene estadisticas de un usuario.
    API compatible con v1.

    Retorna:
        total_requested: Canciones que el usuario pidio
        total_listened: Canciones que escucho (estuvo presente)
        total_time: Tiempo total escuchado en segundos
        first_play: Primera reproduccion
        last_play: Ultima reproduccion
    """
    return get_user_stats_v2(user_id, guild_id)


def get_user_top_songs(user_id: int, guild_id: Optional[int] = None,
                       limit: int = 10) -> List[Tuple[str, str, int]]:
    """
    Top canciones pedidas por un usuario.
    API compatible con v1.

    Retorna: lista de (song_title, artist, request_count)
    """
    return get_user_top_songs_v2(user_id, guild_id, limit)


def get_server_top_users(guild_id: int, limit: int = 10) -> List[Tuple[int, str, int, int]]:
    """
    Top usuarios del servidor por canciones pedidas.
    API compatible con v1.

    Retorna: lista de (user_id, user_name, request_count, total_time)
    """
    return get_server_top_users_v2(guild_id, limit)


def get_server_top_songs(guild_id: int, limit: int = 10) -> List[Tuple[str, str, int]]:
    """
    Top canciones del servidor por veces pedidas.
    API compatible con v1.

    Retorna: lista de (song_title, artist, request_count)
    """
    return get_server_top_songs_v2(guild_id, limit)


def get_user_history(user_id: int, guild_id: Optional[int] = None,
                     limit: int = 20) -> List[Tuple[str, str, str]]:
    """
    Historial reciente de canciones pedidas por un usuario.
    API compatible con v1.

    Retorna: lista de (song_title, artist, played_at)
    """
    return get_user_history_v2(user_id, guild_id, limit)


# ============================================
# NEW V2 FUNCTIONS (Extended API)
# ============================================

def get_top_artists(user_id: int, guild_id: Optional[int] = None,
                    limit: int = 10, year: int = None) -> List[Tuple[str, int, int]]:
    """
    Top artistas para un usuario.
    Nueva funcion en v2.

    Retorna: lista de (artist_name, play_count, total_time_seconds)
    """
    return get_user_top_artists(user_id, guild_id, limit, year)


def get_yearly_stats(user_id: int, guild_id: int, year: int) -> Optional[Dict[str, Any]]:
    """
    Obtiene estadisticas anuales completas para Wrapped.
    Nueva funcion en v2.

    Retorna diccionario con:
        - year, total_plays, total_time_seconds
        - unique_tracks, unique_artists
        - top_tracks, top_artists
        - favorite_hour, favorite_day_of_week
        - first_track, longest_streak, current_streak
        - listening_personality
    """
    return get_user_yearly_stats(user_id, guild_id, year)


def get_listening_hours(user_id: int, guild_id: int,
                        year: int = None) -> Dict[int, int]:
    """
    Obtiene el conteo de reproducciones por hora del dia.
    Nueva funcion en v2.

    Retorna: diccionario {hora: conteo}
    """
    return get_user_listening_hours(user_id, guild_id, year)


def get_listening_days(user_id: int, guild_id: int,
                       year: int = None) -> Dict[int, int]:
    """
    Obtiene el conteo de reproducciones por dia de la semana.
    Nueva funcion en v2.

    Retorna: diccionario {dia_semana: conteo} donde 0=Domingo, 6=Sabado
    """
    return get_user_listening_days(user_id, guild_id, year)


def get_streak(user_id: int, guild_id: int) -> Dict[str, Any]:
    """
    Obtiene informacion de la racha del usuario.
    Nueva funcion en v2.

    Retorna diccionario con:
        - current_streak, longest_streak
        - last_listen_date, streak_start_date
    """
    from core.database.queries import get_user_id_from_discord, get_guild_id_from_discord
    conn = get_connection()
    internal_user_id = get_user_id_from_discord(user_id, conn)
    internal_guild_id = get_guild_id_from_discord(guild_id, conn)
    conn.close()

    if not internal_user_id or not internal_guild_id:
        return {
            'current_streak': 0,
            'longest_streak': 0,
            'last_listen_date': None,
            'streak_start_date': None
        }

    return get_user_streak(internal_user_id, internal_guild_id)


def get_database_status() -> Dict[str, Any]:
    """
    Obtiene el estado actual de la base de datos.
    Util para debugging y administracion.
    """
    from core.database.migrations import get_migration_status
    return get_migration_status()
