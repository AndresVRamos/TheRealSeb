"""
Utilidades de migración para la base de datos de Music Maniac
Maneja la migración del esquema v1 al esquema v2 normalizado
"""
import sqlite3
import os
import shutil
import logging
from datetime import datetime
from typing import Optional

from core.config import STATS_DATABASE_PATH
from .schema import init_database_v2, get_connection, check_v1_tables_exist, get_schema_version
from .queries import (
    get_or_create_user,
    get_or_create_guild,
    get_or_create_artist,
    get_or_create_track,
    update_user_streak
)


def create_backup(suffix: str = None) -> str:
    """Crea un backup de la base de datos actual."""
    if not os.path.exists(STATS_DATABASE_PATH):
        return None

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    suffix = suffix or timestamp
    backup_path = f"{STATS_DATABASE_PATH}.backup_{suffix}"

    shutil.copy2(STATS_DATABASE_PATH, backup_path)
    logging.info(f"Backup de base de datos creado: {backup_path}")
    return backup_path


def migrate_from_v1(force: bool = False) -> bool:
    """
    Migra datos del esquema v1 al esquema v2.

    Args:
        force: Si es True, migra incluso si las tablas v2 ya existen

    Returns:
        True si se realizó la migración, False en caso contrario
    """
    # Verificar si existen tablas v1
    if not check_v1_tables_exist():
        logging.info("No se encontraron tablas v1, omitiendo migración")
        return False

    # Verificar si ya se migró
    current_version = get_schema_version()
    if current_version and current_version >= 2 and not force:
        logging.info("Base de datos ya está en v2, omitiendo migración")
        return False

    logging.info("Iniciando migración de v1 a v2...")

    # Crear backup antes de migrar
    backup_path = create_backup("pre_migration_v2")
    if backup_path:
        logging.info(f"Backup creado en: {backup_path}")

    # Abrir conexión directa (sin row_factory para esta operación)
    conn = sqlite3.connect(STATS_DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Paso 1: Leer todos los datos de v1 ANTES de renombrar tablas
        logging.info("Leyendo datos v1...")

        cursor.execute('''
            SELECT id, requester_id, requester_name, guild_id, song_title, artist, url, duration, played_at
            FROM requests
            ORDER BY played_at ASC
        ''')
        old_requests = cursor.fetchall()
        logging.info(f"Encontrados {len(old_requests)} requests para migrar")

        cursor.execute('''
            SELECT request_id, user_id, user_name
            FROM listens
        ''')
        old_listens = cursor.fetchall()
        logging.info(f"Encontrados {len(old_listens)} listens para migrar")

        # Construir lookup de listens por request_id
        listens_by_request = {}
        for listen in old_listens:
            request_id = listen['request_id']
            if request_id not in listens_by_request:
                listens_by_request[request_id] = []
            listens_by_request[request_id].append({
                'user_id': listen['user_id'],
                'user_name': listen['user_name']
            })

        # Paso 2: Renombrar tablas v1 para evitar conflictos
        logging.info("Renombrando tablas v1...")
        cursor.execute("ALTER TABLE requests RENAME TO requests_v1_backup")
        cursor.execute("ALTER TABLE listens RENAME TO listens_v1_backup")
        conn.commit()

        # Paso 3: Cerrar conexión y crear esquema v2
        conn.close()
        logging.info("Creando esquema v2...")
        init_database_v2()

        # Paso 4: Reabrir conexión para migrar datos
        conn = get_connection()
        cursor = conn.cursor()

        # Cache de guilds
        guild_cache = {}

        # Migrar cada request
        migrated_count = 0
        for request in old_requests:
            old_id = request['id']
            guild_discord_id = request['guild_id']
            requester_discord_id = request['requester_id']
            requester_name = request['requester_name']
            song_title = request['song_title']
            artist = request['artist']
            url = request['url']
            duration = request['duration']
            played_at = request['played_at']

            # Obtener o crear guild
            if guild_discord_id not in guild_cache:
                guild_cache[guild_discord_id] = f"Server {guild_discord_id}"
            guild_name = guild_cache[guild_discord_id]
            guild_id = get_or_create_guild(guild_discord_id, guild_name, conn=conn)

            # Obtener o crear requester
            requester_id = get_or_create_user(requester_discord_id, requester_name, conn=conn)

            # Obtener o crear artista
            artist_id = None
            if artist:
                artist_id = get_or_create_artist(artist, conn=conn)

            # Obtener o crear track
            track_id = get_or_create_track(
                title=song_title,
                artist_id=artist_id,
                duration_seconds=duration,
                url=url,
                conn=conn
            )

            # Insertar registro de play
            cursor.execute('''
                INSERT INTO plays (guild_id, requester_id, track_id, url, played_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (guild_id, requester_id, track_id, url, played_at))
            play_id = cursor.lastrowid

            # Migrar listeners para este request
            listeners = listens_by_request.get(old_id, [])
            for listener in listeners:
                listener_id = get_or_create_user(
                    listener['user_id'],
                    listener['user_name'],
                    conn=conn
                )
                try:
                    cursor.execute('''
                        INSERT INTO listens (play_id, user_id)
                        VALUES (?, ?)
                    ''', (play_id, listener_id))
                except sqlite3.IntegrityError:
                    pass  # Duplicado, omitir

            # Actualizar racha del requester
            if played_at:
                date_key = played_at[:10]  # Extraer 'YYYY-MM-DD'
                update_user_streak(requester_id, guild_id, date_key, conn)

            migrated_count += 1
            if migrated_count % 100 == 0:
                logging.info(f"Migrados {migrated_count}/{len(old_requests)} requests...")
                conn.commit()

        conn.commit()
        logging.info(f"¡Migración completa! Migrados {migrated_count} requests")

        # Recalcular stats cacheadas
        _recalculate_cached_stats(conn)

        # Marcar migración como completa
        cursor.execute('''
            INSERT OR REPLACE INTO schema_metadata (key, value)
            VALUES ('migration_v1_to_v2_completed', ?)
        ''', (datetime.now().isoformat(),))

        conn.commit()
        conn.close()

        logging.info("¡Migración de v1 a v2 completada exitosamente!")
        return True

    except Exception as e:
        conn.rollback()
        conn.close()
        logging.error(f"Migración falló: {e}")
        raise


def _recalculate_cached_stats(conn: sqlite3.Connection):
    """Recalcula todas las estadísticas cacheadas después de la migración."""
    cursor = conn.cursor()
    logging.info("Recalculando stats cacheadas...")

    # Actualizar stats de usuarios
    cursor.execute('''
        UPDATE users SET
            total_plays = (
                SELECT COUNT(*) FROM plays WHERE requester_id = users.id
            ),
            total_listens = (
                SELECT COUNT(*) FROM listens WHERE user_id = users.id
            ),
            total_time_seconds = (
                SELECT COALESCE(SUM(t.duration_seconds), 0)
                FROM plays p
                JOIN tracks t ON p.track_id = t.id
                WHERE p.requester_id = users.id
            )
    ''')

    # Actualizar stats de guilds
    cursor.execute('''
        UPDATE guilds SET
            total_plays = (
                SELECT COUNT(*) FROM plays WHERE guild_id = guilds.id
            ),
            total_unique_users = (
                SELECT COUNT(DISTINCT requester_id) FROM plays WHERE guild_id = guilds.id
            ),
            total_time_seconds = (
                SELECT COALESCE(SUM(t.duration_seconds), 0)
                FROM plays p
                JOIN tracks t ON p.track_id = t.id
                WHERE p.guild_id = guilds.id
            )
    ''')

    conn.commit()
    logging.info("Stats cacheadas recalculadas")


def check_migration_needed() -> bool:
    """Verifica si se necesita migración de v1 a v2."""
    if not os.path.exists(STATS_DATABASE_PATH):
        return False

    has_v1 = check_v1_tables_exist()
    current_version = get_schema_version()

    return has_v1 and (current_version is None or current_version < 2)


def get_migration_status() -> dict:
    """Obtiene el estado actual de migración/esquema."""
    status = {
        'database_exists': os.path.exists(STATS_DATABASE_PATH),
        'has_v1_tables': False,
        'schema_version': None,
        'migration_needed': False,
        'migration_completed': None
    }

    if not status['database_exists']:
        return status

    status['has_v1_tables'] = check_v1_tables_exist()
    status['schema_version'] = get_schema_version()
    status['migration_needed'] = check_migration_needed()

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM schema_metadata WHERE key = 'migration_v1_to_v2_completed'")
        row = cursor.fetchone()
        if row:
            status['migration_completed'] = row['value']
        conn.close()
    except:
        pass

    return status
