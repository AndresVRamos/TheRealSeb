"""
Modulo de BD para el bot
"""

from .schema import init_database, get_connection
from .queries import (
    record_play,
    get_or_create_user,
    get_or_create_artist,
    get_or_create_track,
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
)

__all__ = [
    'init_database',
    'get_connection',
    'record_play',
    'get_or_create_user',
    'get_or_create_artist',
    'get_or_create_track',
    'get_user_stats',
    'get_user_top_songs',
    'get_user_top_artists',
    'get_server_top_songs',
    'get_server_top_users',
    'get_server_stats',
    'get_user_history',
    'get_user_yearly_stats',
    'get_user_listening_hours',
    'get_user_listening_days',
    'get_user_streak',
    'update_user_streak',
]
