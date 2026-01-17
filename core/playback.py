"""
Funciones reutilizables para controlar la reproducción de música
"""
import time
import random
import logging


async def pause_playback(guild_id, song_data, voice_clients):
    """
    Pausa la reproducción y registra el tiempo de pausa

    Returns:
        bool: True si se pausó correctamente, False si no se pudo pausar
    """
    if guild_id not in voice_clients:
        return False

    vc = voice_clients[guild_id]

    if not vc.is_playing():
        return False

    vc.pause()

    if guild_id in song_data:
        song_data[guild_id]['pause_start_time'] = time.time()

    logging.info(f"Reproducción pausada en guild {guild_id}")
    return True


async def resume_playback(guild_id, song_data, voice_clients):
    """
    Reanuda la reproducción y actualiza el tiempo de pausa

    Returns:
        bool: True si se reanudó correctamente, False si no se pudo reanudar
    """
    if guild_id not in voice_clients:
        return False

    vc = voice_clients[guild_id]

    if not vc.is_paused():
        return False

    vc.resume()

    if guild_id in song_data and song_data[guild_id]['pause_start_time'] > 0:
        paused_duration = time.time() - song_data[guild_id]['pause_start_time']
        song_data[guild_id]['paused_time'] += paused_duration
        song_data[guild_id]['pause_start_time'] = 0

    logging.info(f"Reproducción reanudada en guild {guild_id}")
    return True


async def skip_song(guild_id, voice_clients):
    """
    Salta a la siguiente canción

    Returns:
        bool: True si se saltó correctamente, False si no se pudo saltar
    """
    if guild_id not in voice_clients:
        return False

    vc = voice_clients[guild_id]

    if not (vc.is_playing() or vc.is_paused()):
        return False

    vc.stop()  # El callback after_play() manejará la siguiente canción
    logging.info(f"Canción saltada en guild {guild_id}")
    return True


def toggle_loop(guild_id, loop_status):
    """
    Activa o desactiva el loop de la canción actual

    Returns:
        bool: El nuevo estado del loop (True si está activado, False si está desactivado)
    """
    loop_status[guild_id] = not loop_status.get(guild_id, False)
    logging.info(f"Loop {'activado' if loop_status[guild_id] else 'desactivado'} en guild {guild_id}")
    return loop_status[guild_id]


async def shuffle_queue(guild_id, queues):
    """
    Mezcla aleatoriamente la queue

    Returns:
        bool: True si se mezcló correctamente, False si no se pudo mezclar
    """
    if guild_id not in queues or len(queues[guild_id]) < 2:
        return False

    random.shuffle(queues[guild_id])
    logging.info(f"Queue mezclada en guild {guild_id}")
    return True


async def stop_playback(guild_id, voice_clients, queues, manual_stop):
    """
    Detiene la reproducción y limpia la queue

    Returns:
        bool: True si se detuvo correctamente, False si no se pudo detener
    """
    if guild_id not in voice_clients:
        return False

    vc = voice_clients[guild_id]

    if not vc.is_connected():
        return False

    # Marcar manual_stop ANTES de detener (CRÍTICO para evitar auto-continue)
    manual_stop[guild_id] = True

    vc.stop()

    if guild_id in queues:
        queues[guild_id].clear()

    logging.info(f"Reproducción detenida y queue limpiada en guild {guild_id}")
    return True
