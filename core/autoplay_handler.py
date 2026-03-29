"""
Handler para la funcionalidad de autoplay/radio
Usa videos relacionados de YouTube + busqueda como fallback
"""
import logging
import asyncio
import random
import re
from typing import Optional, Tuple, Set, List

from core.youtube_handler import search_youtube_multiple, extract_video_info, get_related_videos, get_mix_playlist_videos
from core.config import AUTOPLAY_SEARCH_TIMEOUT

# Palabras que indican que NO es una cancion
BLACKLIST_WORDS = [
    'tutorial', 'how to', 'howto', 'cover', 'piano cover', 'guitar cover',
    'reaction', 'react', 'review', 'minecraft', 'roblox', 'fortnite',
    'karaoke', 'nightcore', 'slowed', '8d audio',
    'bass boosted', 'sub español',
    'amv', 'gmv', 'pmv', 'meme', 'animation', 'animacion', 'animated',
    'piano tutorial', 'guitar tutorial', 'drum cover', 'bass cover',
    'behind the scenes', 'making of', 'interview', 'podcast',
    'compilation', 'mashup', '1 hour', '10 hours', 'extended',
    'speed up', 'sped up'
]

MAX_DURATION = 600  # 10 minutos


async def get_related_song(
    ytdl,
    current_song_data: dict,
    played_history: Set[str],
    sp=None
) -> Optional[Tuple[str, str, int]]:
    """
    Encuentra una cancion relacionada usando videos relacionados de YouTube.
    Estrategias:
    1. YouTube Mix playlist (mas confiable)
    2. related_videos de yt-dlp (requiere JS runtime)
    3. Busqueda por contexto (fallback)
    """
    current_url = current_song_data.get('url', '')
    title = current_song_data.get('title', '')
    song_name = _extract_song_name(title)

    logging.info(f"Autoplay: Buscando cancion relacionada para: {title}")

    # Estrategia 1: Videos relacionados de YouTube (incluye Mix playlist)
    if current_url:
        result = await _get_from_related_videos(ytdl, current_url, song_name, played_history)
        if result:
            return result

    # Estrategia 2: Busqueda de mixes basados en titulo
    logging.info("Autoplay: Intentando busqueda de mixes...")
    result = await _search_music_mix(ytdl, title, song_name, played_history)
    if result:
        return result

    # Estrategia 3: Fallback a busqueda por contexto
    logging.info("Autoplay: Usando busqueda por contexto...")
    context = _extract_context_from_title(title)
    if context:
        return await _search_different_song(ytdl, context, song_name, played_history)

    return None


async def _search_music_mix(
    ytdl,
    title: str,
    current_song_name: str,
    played_history: Set[str]
) -> Optional[Tuple[str, str, int]]:
    """
    Busca mixes de musica basados en el titulo actual.
    """
    # Limpiar el titulo para busqueda
    clean_title = re.sub(r'\([^)]*\)', '', title)
    clean_title = re.sub(r'\[[^\]]*\]', '', clean_title)
    clean_title = clean_title.strip()

    queries = [
        f"{clean_title} mix",
        f"{clean_title} playlist",
    ]

    for query in queries:
        logging.info(f"Autoplay: Buscando mix con: '{query}'")

        try:
            urls = await asyncio.wait_for(
                search_youtube_multiple(query, max_results=5),
                timeout=AUTOPLAY_SEARCH_TIMEOUT
            )

            for url in urls:
                # Verificar si es una playlist/mix
                if 'list=' in url:
                    # Es un mix, extraer canciones
                    result = await _get_song_from_mix_url(ytdl, url, current_song_name, played_history)
                    if result:
                        return result

        except asyncio.TimeoutError:
            logging.warning(f"Autoplay: Timeout buscando mix")
            continue
        except Exception as e:
            logging.error(f"Autoplay: Error buscando mix: {e}")
            continue

    return None


async def _get_song_from_mix_url(
    ytdl,
    mix_url: str,
    current_song_name: str,
    played_history: Set[str]
) -> Optional[Tuple[str, str, int]]:
    """
    Extrae una cancion de un mix/playlist URL.
    Selecciona aleatoriamente entre los videos validos.
    """
    try:
        # Extraer video_id del mix URL para excluirlo
        original_id = ""
        if 'watch?v=' in mix_url:
            match = re.search(r'watch\?v=([^&]+)', mix_url)
            if match:
                original_id = match.group(1)

        videos = await get_mix_playlist_videos(mix_url, original_id, limit=15)

        # Recolectar videos validos
        valid_videos = []

        for video in videos:
            video_url = video.get('url', '')
            video_title = video.get('title', '')
            video_duration = video.get('duration', 0)

            if not video_url or video_url in played_history:
                continue

            if _is_same_song(video_title, current_song_name):
                continue

            # Si no tenemos duracion, obtenerla
            if not video_duration:
                try:
                    full_info = await extract_video_info(ytdl, video_url)
                    if full_info:
                        video_title = full_info.get('title', video_title)
                        video_duration = full_info.get('duration', 0)
                except Exception:
                    continue

            if not _is_valid_music_video(video_title, video_duration):
                continue

            valid_videos.append((video_url, video_title, video_duration))

        if valid_videos:
            selected = random.choice(valid_videos)
            logging.info(f"Autoplay: Encontrado en mix ({len(valid_videos)} opciones): {selected[1]}")
            return selected

    except Exception as e:
        logging.debug(f"Autoplay: Error extrayendo de mix: {e}")

    return None


async def _get_from_related_videos(
    ytdl,
    current_url: str,
    current_song_name: str,
    played_history: Set[str]
) -> Optional[Tuple[str, str, int]]:
    """
    Obtiene una cancion de los videos relacionados de YouTube.
    Selecciona aleatoriamente entre los videos validos para evitar bucles.
    """
    try:
        logging.info("Autoplay: Extrayendo videos relacionados de YouTube...")

        related_videos = await get_related_videos(current_url, limit=20)

        if not related_videos:
            logging.info("Autoplay: No se encontraron videos relacionados")
            return None

        logging.info(f"Autoplay: Procesando {len(related_videos)} videos relacionados")

        # Recolectar todos los videos validos
        valid_videos = []

        for video in related_videos:
            video_url = video.get('url', '')
            video_title = video.get('title', '')
            video_duration = video.get('duration', 0)

            if not video_url:
                continue

            if video_url in played_history:
                logging.info(f"Autoplay: '{video_title[:30]}' ya reproducido")
                continue

            # Verificar que no sea la misma cancion
            if _is_same_song(video_title, current_song_name):
                logging.info(f"Autoplay: Saltando '{video_title[:30]}' - misma cancion")
                continue

            # Si no tenemos duracion, obtenerla
            if not video_duration:
                try:
                    full_info = await extract_video_info(ytdl, video_url)
                    if full_info:
                        video_title = full_info.get('title', video_title)
                        video_duration = full_info.get('duration', 0)
                except Exception as e:
                    logging.warning(f"Autoplay: Error obteniendo info: {e}")
                    continue

            # Verificar filtros
            if not _is_valid_music_video(video_title, video_duration):
                continue

            valid_videos.append((video_url, video_title, video_duration))

        if not valid_videos:
            logging.info("Autoplay: Ningun video relacionado paso los filtros")
            return None

        # Seleccionar aleatoriamente de los videos validos
        selected = random.choice(valid_videos)
        logging.info(f"Autoplay: Seleccionado aleatoriamente ({len(valid_videos)} opciones): {selected[1]}")
        return selected

    except Exception as e:
        logging.error(f"Autoplay: Error obteniendo relacionados: {e}")
        return None


async def _search_different_song(
    ytdl,
    context: str,
    current_song_name: str,
    played_history: Set[str]
) -> Optional[Tuple[str, str, int]]:
    """
    Busca una cancion diferente del mismo contexto.
    Selecciona aleatoriamente entre los resultados validos.
    """
    queries = [
        f"{context} soundtrack",
        f"{context} ost",
        f"{context} music",
        context
    ]

    # Recolectar videos validos de todas las queries
    valid_videos = []

    for query in queries:
        logging.info(f"Autoplay: Buscando con query: '{query}'")

        try:
            urls = await asyncio.wait_for(
                search_youtube_multiple(query, max_results=15),
                timeout=AUTOPLAY_SEARCH_TIMEOUT
            )

            for url in urls:
                if url in played_history:
                    continue

                video_info = await extract_video_info(ytdl, url)
                if not video_info:
                    continue

                video_title = video_info.get('title', '')
                duration = video_info.get('duration', 0)

                if _is_same_song(video_title, current_song_name):
                    logging.info(f"Autoplay: Saltando '{video_title[:30]}' - misma cancion")
                    continue

                if not _is_valid_music_video(video_title, duration):
                    continue

                valid_videos.append((url, video_title, duration))

            # Si encontramos suficientes videos, salir del loop
            if len(valid_videos) >= 5:
                break

        except asyncio.TimeoutError:
            logging.warning(f"Autoplay: Timeout con query: {query}")
            continue
        except Exception as e:
            logging.error(f"Autoplay: Error: {e}")
            continue

    if valid_videos:
        selected = random.choice(valid_videos)
        logging.info(f"Autoplay: Seleccionado en busqueda ({len(valid_videos)} opciones): {selected[1]}")
        return selected

    logging.info("Autoplay: No se encontro ninguna cancion")
    return None


def _extract_context_from_title(title: str) -> str:
    """Extrae el contexto (artista/juego/serie) del titulo."""
    if not title:
        return ""

    separators = [' - ', ' – ', ' — ', ' | ', ' // ', ': ']

    for sep in separators:
        if sep in title:
            parts = title.split(sep)
            if len(parts) >= 2:
                candidate = parts[0].strip()
                candidate = re.sub(r'\([^)]*\)', '', candidate)
                candidate = re.sub(r'\[[^\]]*\]', '', candidate)
                candidate = re.sub(r'^\d+\.?\s*', '', candidate)
                candidate = candidate.strip()
                if 2 < len(candidate) < 50:
                    return candidate

    return ""


def _extract_song_name(title: str) -> str:
    """Extrae el nombre de la cancion del titulo."""
    if not title:
        return ""

    separators = [' - ', ' – ', ' — ', ' | ', ' // ', ': ']

    for sep in separators:
        if sep in title:
            parts = title.split(sep)
            if len(parts) >= 2:
                song = parts[-1].strip()
                song = re.sub(r'\([^)]*\)', '', song)
                song = re.sub(r'\[[^\]]*\]', '', song)
                return song.strip().lower()

    # Si no hay separador, usar el titulo limpio
    clean = re.sub(r'\([^)]*\)', '', title)
    clean = re.sub(r'\[[^\]]*\]', '', clean)
    clean = re.sub(r'^\d+\.?\s*', '', clean)
    return clean.strip().lower()


def _is_same_song(video_title: str, current_song_name: str) -> bool:
    """Verifica si un video es la misma cancion."""
    if not current_song_name:
        return False

    video_clean = re.sub(r'[^\w\s]', '', video_title.lower())
    song_clean = re.sub(r'[^\w\s]', '', current_song_name.lower())

    song_words = [w for w in song_clean.split() if len(w) > 2]
    if not song_words:
        return False

    matches = sum(1 for word in song_words if word in video_clean)
    match_ratio = matches / len(song_words)

    return match_ratio >= 0.8


def _is_valid_music_video(title: str, duration: int) -> bool:
    """Verifica si un video parece ser musica real."""
    title_lower = title.lower()

    for word in BLACKLIST_WORDS:
        if word in title_lower:
            logging.info(f"Autoplay: Rechazado '{title[:40]}' - contiene '{word}'")
            return False

    if duration > MAX_DURATION:
        logging.info(f"Autoplay: Rechazado '{title[:40]}' - muy largo ({duration}s)")
        return False

    return True
