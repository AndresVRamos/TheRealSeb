"""
Esquema de base de datos para el bot Music Maniac
Esquema normalizado con soporte para estadísticas estilo Wrapped
"""
import sqlite3
import os
import logging
from typing import Optional

from core.config import STATS_DATABASE_PATH

# Schema version
SCHEMA_VERSION = 2


def get_connection() -> sqlite3.Connection:
    """Obtiene una conexión a la base de datos con row_factory habilitado"""
    conn = sqlite3.connect(STATS_DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Inicializa el esquema de la base de datos con todas las tablas e índices"""
    os.makedirs(os.path.dirname(STATS_DATABASE_PATH), exist_ok=True)
    conn = get_connection()
    cursor = conn.cursor()

    # Habilitar claves foráneas
    cursor.execute("PRAGMA foreign_keys = ON")

    # ============================================
    # TABLA DE METADATOS (para versionado de esquema)
    # ============================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS schema_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')

    # ============================================
    # TABLAS NORMALIZADAS PRINCIPALES
    # ============================================

    # Tabla de usuarios - Usuarios de Discord con estadísticas en caché
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            discord_id INTEGER NOT NULL UNIQUE,
            username TEXT NOT NULL,
            display_name TEXT,
            avatar_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            -- Estadísticas en caché (actualizadas por disparadores/tareas)
            total_plays INTEGER DEFAULT 0,
            total_listens INTEGER DEFAULT 0,
            total_time_seconds INTEGER DEFAULT 0
        )
    ''')

    # Tabla de gremios - Servidores de Discord con estadísticas en caché
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS guilds (
            id INTEGER PRIMARY KEY,
            discord_id INTEGER NOT NULL UNIQUE,
            name TEXT NOT NULL,
            icon_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            -- Estadísticas en caché
            total_plays INTEGER DEFAULT 0,
            total_unique_users INTEGER DEFAULT 0,
            total_time_seconds INTEGER DEFAULT 0
        )
    ''')

    # Tabla de artistas - Artistas normalizados
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS artists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            name_normalized TEXT NOT NULL,
            image_url TEXT,
            spotify_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(name_normalized)
        )
    ''')

    # Tabla de pistas - Pistas normalizadas con identificadores únicos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tracks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            title_normalized TEXT NOT NULL,
            artist_id INTEGER,
            duration_seconds INTEGER,
            youtube_id TEXT,
            spotify_id TEXT,
            thumbnail_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (artist_id) REFERENCES artists(id),
            UNIQUE(title_normalized, artist_id)
        )
    ''')

    # URLs de pistas - Múltiples URLs pueden apuntar a la misma pista
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS track_urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id INTEGER NOT NULL,
            url TEXT NOT NULL UNIQUE,
            source TEXT NOT NULL, -- 'youtube', 'spotify', etc.
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (track_id) REFERENCES tracks(id)
        )
    ''')

    # ============================================
    # EVENTOS DE REPRODUCCIÓN (Tabla de eventos principal)
    # ============================================

    # Tabla de reproducciones - Cada evento de reproducción
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS plays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            requester_id INTEGER NOT NULL,
            track_id INTEGER NOT NULL,
            url TEXT,
            played_at TIMESTAMP NOT NULL,
            -- Columnas calculadas para consultas rápidas
            year INTEGER GENERATED ALWAYS AS (CAST(strftime('%Y', played_at) AS INTEGER)) STORED,
            month INTEGER GENERATED ALWAYS AS (CAST(strftime('%m', played_at) AS INTEGER)) STORED,
            day INTEGER GENERATED ALWAYS AS (CAST(strftime('%d', played_at) AS INTEGER)) STORED,
            hour INTEGER GENERATED ALWAYS AS (CAST(strftime('%H', played_at) AS INTEGER)) STORED,
            day_of_week INTEGER GENERATED ALWAYS AS (CAST(strftime('%w', played_at) AS INTEGER)) STORED,
            week_of_year INTEGER GENERATED ALWAYS AS (CAST(strftime('%W', played_at) AS INTEGER)) STORED,
            date_key TEXT GENERATED ALWAYS AS (strftime('%Y-%m-%d', played_at)) STORED,
            FOREIGN KEY (guild_id) REFERENCES guilds(id),
            FOREIGN KEY (requester_id) REFERENCES users(id),
            FOREIGN KEY (track_id) REFERENCES tracks(id)
        )
    ''')

    # Tabla de escuchas - Usuarios que estuvieron presentes durante una reproducción
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS listens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            play_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            FOREIGN KEY (play_id) REFERENCES plays(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(play_id, user_id)
        )
    ''')

    # ============================================
    # TABLAS DE AGREGACIÓN (Caché de rendimiento)
    # ============================================

    # Estadísticas diarias por usuario por gremio
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_stats_user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            date_key TEXT NOT NULL, -- 'AAAA-MM-DD'
            plays_count INTEGER DEFAULT 0,
            listens_count INTEGER DEFAULT 0,
            time_seconds INTEGER DEFAULT 0,
            unique_tracks INTEGER DEFAULT 0,
            unique_artists INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (guild_id) REFERENCES guilds(id),
            UNIQUE(user_id, guild_id, date_key)
        )
    ''')

    # Estadísticas mensuales por usuario por gremio
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS monthly_stats_user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            plays_count INTEGER DEFAULT 0,
            listens_count INTEGER DEFAULT 0,
            time_seconds INTEGER DEFAULT 0,
            unique_tracks INTEGER DEFAULT 0,
            unique_artists INTEGER DEFAULT 0,
            top_track_id INTEGER,
            top_artist_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (guild_id) REFERENCES guilds(id),
            FOREIGN KEY (top_track_id) REFERENCES tracks(id),
            FOREIGN KEY (top_artist_id) REFERENCES artists(id),
            UNIQUE(user_id, guild_id, year, month)
        )
    ''')

    # Estadísticas anuales por usuario por gremio (para Wrapped)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS yearly_stats_user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            plays_count INTEGER DEFAULT 0,
            listens_count INTEGER DEFAULT 0,
            time_seconds INTEGER DEFAULT 0,
            unique_tracks INTEGER DEFAULT 0,
            unique_artists INTEGER DEFAULT 0,
            -- Campos específicos de Wrapped
            top_track_id INTEGER,
            top_artist_id INTEGER,
            first_track_id INTEGER, -- Primera canción del año
            first_play_date TIMESTAMP,
            favorite_hour INTEGER, -- 0-23
            favorite_day_of_week INTEGER, -- 0=Domingo, 6=Sábado
            longest_streak_days INTEGER DEFAULT 0,
            listening_personality TEXT, -- 'Explorer', 'Loyalist', 'Night Owl', etc.
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (guild_id) REFERENCES guilds(id),
            FOREIGN KEY (top_track_id) REFERENCES tracks(id),
            FOREIGN KEY (top_artist_id) REFERENCES artists(id),
            FOREIGN KEY (first_track_id) REFERENCES tracks(id),
            UNIQUE(user_id, guild_id, year)
        )
    ''')

    # Rachas de usuario - Rastrear días de escucha consecutivos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_streaks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            current_streak INTEGER DEFAULT 0,
            longest_streak INTEGER DEFAULT 0,
            last_listen_date TEXT, -- 'AAAA-MM-DD'
            streak_start_date TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (guild_id) REFERENCES guilds(id),
            UNIQUE(user_id, guild_id)
        )
    ''')

    # ============================================
    # ÍNDICES PARA EL RENDIMIENTO
    # ============================================

    # Índices de usuarios
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_discord_id ON users(discord_id)')

    # Índices de gremios
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_guilds_discord_id ON guilds(discord_id)')

    # Índices de artistas
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_artists_name_normalized ON artists(name_normalized)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_artists_spotify_id ON artists(spotify_id)')

    # Índices de pistas
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tracks_title_normalized ON tracks(title_normalized)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tracks_artist_id ON tracks(artist_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tracks_youtube_id ON tracks(youtube_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tracks_spotify_id ON tracks(spotify_id)')

    # Índices de URLs de pistas
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_track_urls_track_id ON track_urls(track_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_track_urls_url ON track_urls(url)')

    # Índices de reproducciones - Críticos para el rendimiento
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_plays_guild_id ON plays(guild_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_plays_requester_id ON plays(requester_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_plays_track_id ON plays(track_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_plays_played_at ON plays(played_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_plays_year ON plays(year)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_plays_year_month ON plays(year, month)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_plays_date_key ON plays(date_key)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_plays_guild_year ON plays(guild_id, year)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_plays_requester_guild ON plays(requester_id, guild_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_plays_hour ON plays(hour)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_plays_day_of_week ON plays(day_of_week)')

    # Índices de escuchas
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_listens_play_id ON listens(play_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_listens_user_id ON listens(user_id)')

    # Índices de tablas de agregación
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_daily_stats_user_date ON daily_stats_user(user_id, guild_id, date_key)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_monthly_stats_user_period ON monthly_stats_user(user_id, guild_id, year, month)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_yearly_stats_user_year ON yearly_stats_user(user_id, guild_id, year)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_streaks_user_guild ON user_streaks(user_id, guild_id)')

    # ============================================
    # DISPARADORES PARA ACTUALIZACIONES AUTOMÁTICAS DE CACHÉ
    # ============================================

    # Disparador: Actualizar estadísticas de usuario en nueva reproducción (como solicitante)
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS update_user_stats_on_play
        AFTER INSERT ON plays
        BEGIN
            UPDATE users
            SET total_plays = total_plays + 1,
                total_time_seconds = total_time_seconds + COALESCE(
                    (SELECT duration_seconds FROM tracks WHERE id = NEW.track_id), 0
                ),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = NEW.requester_id;
        END
    ''')

    # Disparador: Actualizar estadísticas de usuario en nueva escucha
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS update_user_stats_on_listen
        AFTER INSERT ON listens
        BEGIN
            UPDATE users
            SET total_listens = total_listens + 1,
                total_time_seconds = total_time_seconds + COALESCE(
                    (SELECT t.duration_seconds
                     FROM plays p
                     JOIN tracks t ON p.track_id = t.id
                     WHERE p.id = NEW.play_id), 0
                ),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = NEW.user_id;
        END
    ''')

    # Disparador: Actualizar estadísticas de gremio en nueva reproducción
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS update_guild_stats_on_play
        AFTER INSERT ON plays
        BEGIN
            UPDATE guilds
            SET total_plays = total_plays + 1,
                total_time_seconds = total_time_seconds + COALESCE(
                    (SELECT duration_seconds FROM tracks WHERE id = NEW.track_id), 0
                ),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = NEW.guild_id;
        END
    ''')

    # Establecer la versión del esquema
    cursor.execute('''
        INSERT OR REPLACE INTO schema_metadata (key, value)
        VALUES ('version', ?)
    ''', (str(SCHEMA_VERSION),))

    conn.commit()
    conn.close()

    logging.info("Base de datos inicializada correctamente")


def get_schema_version() -> Optional[int]:
    """Obtiene la versión actual del esquema de la base de datos"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM schema_metadata WHERE key = 'version'")
        row = cursor.fetchone()
        conn.close()
        return int(row['value']) if row else None
    except sqlite3.OperationalError:
        return None


