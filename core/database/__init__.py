"""
Modulo de BD para el bot
"""

from .schema import init_database_v2, get_connection
from .queries import (
    record_play_v2,
    get_or_create_user,
    get_or_create_artist,
    get_or_create_track,
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
from .migrations import migrate_from_v1

__all__ = [
    'init_database_v2',
    'get_connection',
    'record_play_v2',
    'get_or_create_user',
    'get_or_create_artist',
    'get_or_create_track',
    'get_user_stats_v2',
    'get_user_top_songs_v2',
    'get_user_top_artists',
    'get_server_top_songs_v2',
    'get_server_top_users_v2',
    'get_user_history_v2',
    'get_user_yearly_stats',
    'get_user_listening_hours',
    'get_user_listening_days',
    'get_user_streak',
    'update_user_streak',
    'migrate_from_v1',
]
