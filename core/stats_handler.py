"""
Modulo para manejo de estadisticas de reproducciones con SQLite

Este modulo actua como facade para el sistema de base de datos,
proporcionando una API limpia para los comandos del bot.
"""
import logging
from typing import Optional, List, Tuple, Dict, Any

from core.database.schema import init_database as _init_database, get_connection
from core.database.queries import (
    record_play as _record_play,
    get_user_stats,
    get_user_top_songs,
    get_user_top_artists,
    get_server_top_songs,
    get_server_top_users,
    get_server_stats,
    get_user_history,
    get_user_yearly_stats,
    get_user_listening_hours,
    get_user_listening_days,
    get_user_streak,
    update_user_streak,
    get_user_id_from_discord,
    get_guild_id_from_discord,
)


def init_database():
    """Inicializa la base de datos."""
    try:
        _init_database()
        logging.info("Base de datos inicializada correctamente")
    except Exception as e:
        logging.error(f"Error inicializando base de datos: {e}")
        raise


def record_play(guild_id: int, requester_id: int, requester_name: str,
                song_title: str, artist: Optional[str], url: Optional[str],
                duration: Optional[int], listeners: List[Tuple[int, str]],
                guild_name: str = None, thumbnail_url: str = None,
                guild_icon_url: str = None):
    """
    Registra una reproduccion completa.

    Args:
        guild_id: ID del servidor de Discord
        requester_id: ID del usuario que pidio la cancion
        requester_name: Nombre del usuario que pidio la cancion
        song_title: Titulo de la cancion
        artist: Artista (opcional)
        url: URL de la cancion (opcional)
        duration: Duracion en segundos (opcional)
        listeners: Lista de tuplas (user_id, user_name) de los oyentes
        guild_name: Nombre del servidor (opcional)
        thumbnail_url: URL del thumbnail (opcional)
        guild_icon_url: URL del icono del servidor (opcional)
    """
    try:
        if guild_name is None:
            guild_name = f"Server {guild_id}"

        _record_play(
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


# Re-exportar funciones de queries directamente
__all__ = [
    'init_database',
    'record_play',
    'get_user_stats',
    'get_user_top_songs',
    'get_server_top_users',
    'get_server_top_songs',
    'get_server_stats',
    'get_user_history',
    'get_top_artists',
    'get_yearly_stats',
    'get_listening_hours',
    'get_listening_days',
    'get_streak',
]

def get_top_artists(user_id: int, guild_id: Optional[int] = None,
                    limit: int = 10, year: int = None) -> List[Tuple[str, int, int]]:
    """
    Top artistas para un usuario.

    Retorna: lista de (artist_name, play_count, total_time_seconds)
    """
    return get_user_top_artists(user_id, guild_id, limit, year)


def get_yearly_stats(user_id: int, guild_id: int, year: int) -> Optional[Dict[str, Any]]:
    """
    Obtiene estadisticas anuales completas para Wrapped.

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

    Retorna: diccionario {hora: conteo}
    """
    return get_user_listening_hours(user_id, guild_id, year)


def get_listening_days(user_id: int, guild_id: int,
                       year: int = None) -> Dict[int, int]:
    """
    Obtiene el conteo de reproducciones por dia de la semana.

    Retorna: diccionario {dia_semana: conteo} donde 0=Domingo, 6=Sabado
    """
    return get_user_listening_days(user_id, guild_id, year)


def get_streak(user_id: int, guild_id: int) -> Dict[str, Any]:
    """
    Obtiene informacion de la racha del usuario.

    Retorna diccionario con:
        - current_streak, longest_streak
        - last_listen_date, streak_start_date
    """
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
