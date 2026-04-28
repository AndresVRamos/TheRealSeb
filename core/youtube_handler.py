"""
Handler para búsqueda y extracción de URLs de YouTube
"""
import yt_dlp
import aiohttp
import urllib.parse
import re
import logging
import asyncio

from core.config import SEARCH_SUFFIX


YOUTUBE_BASE_URL = 'https://www.youtube.com/'
YOUTUBE_RESULTS_URL = 'https://www.youtube.com/results?'


class YTDLLogger:
    """Logger personalizado para yt-dlp"""

    def debug(self, msg):
        if msg.startswith('[debug] '):
            pass
        else:
            logging.debug(msg)

    def info(self, msg):
        logging.info(msg)

    def warning(self, msg):
        logging.warning(msg)

    def error(self, msg):
        logging.error(msg)


def create_ytdl():
    """Crear instancia de yt-dlp con configuración óptima"""
    yt_dl_options = {
        "format": "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best",
        "noplaylist": True,
        "extract_flat": "in_playlist",
        "extractor_args": {
            "youtube": {
                "player_client": ["ios", "android", "web"]
            }
        },
        "nocheckcertificate": True,
        "logger": YTDLLogger(),
        "progress_hooks": [],
        "geo_bypass": True,
        "age_limit": None,
    }
    return yt_dlp.YoutubeDL(yt_dl_options)


async def search_youtube(query: str) -> str:
    """
    Busca un video en YouTube y retorna la URL del primer resultado

    Args:
        query: Término de búsqueda

    Returns:
        URL del video de YouTube o None si no se encontró
    """
    # Agregar sufijo para evitar videos musicales
    if SEARCH_SUFFIX:
        query = f"{query} {SEARCH_SUFFIX}"
    logging.info(f"[SEARCH] Buscando en YouTube: '{query}'")
    query_string = urllib.parse.urlencode({'search_query': query})
    async with aiohttp.ClientSession() as session:
        async with session.get(YOUTUBE_RESULTS_URL + query_string) as response:
            content = await response.text()
            search_results = re.findall(r'/watch\?v=(.{11})', content)
            if not search_results:
                logging.error("No se encontraron resultados en YouTube para la búsqueda.")
                return None
            return YOUTUBE_BASE_URL + 'watch?v=' + search_results[0]


async def search_youtube_multiple(query: str, max_results: int = 5) -> list:
    """
    Busca videos en YouTube y retorna múltiples resultados con info básica

    Args:
        query: Término de búsqueda
        max_results: Número máximo de resultados a retornar

    Returns:
        Lista de tuplas (url, title, duration) con información básica
    """
    # Agregar sufijo para evitar videos musicales
    if SEARCH_SUFFIX:
        query = f"{query} {SEARCH_SUFFIX}"
    logging.info(f"[SEARCH] Buscando en YouTube: '{query}'")

    # Usar yt-dlp con ytsearch que ya incluye título y duración
    ytdl = create_ytdl()
    loop = asyncio.get_event_loop()

    try:
        # Usar ytsearchN: para obtener N resultados con metadata básica
        search_query = f"ytsearch{max_results}:{query}"
        data = await loop.run_in_executor(
            None,
            lambda: ytdl.extract_info(search_query, download=False, process=False)
        )

        results = []
        if data and 'entries' in data:
            # entries puede ser un iterador, convertirlo a lista
            count = 0
            for entry in data['entries']:
                if entry and count < max_results:
                    url = YOUTUBE_BASE_URL + 'watch?v=' + entry['id']
                    title = entry.get('title', 'Unknown Title')
                    duration = entry.get('duration', 0)
                    results.append((url, title, duration))
                    count += 1

        return results
    except Exception as e:
        logging.error(f"Error en search_youtube_multiple: {e}")
        return []


async def extract_video_info(ytdl, url: str):
    """
    Extrae información de un video de YouTube

    Args:
        ytdl: Instancia de yt-dlp
        url: URL del video

    Returns:
        Diccionario con información del video (title, url, duration, stream_url)
    """
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))

    if 'url' not in data:
        logging.error(f"No URL found in data. Available keys: {list(data.keys())}")
        return None

    # Intentar obtener el artista de varios campos posibles
    artist = data.get('artist') or data.get('creator') or data.get('uploader') or data.get('channel')

    return {
        'title': data.get('title', 'Unknown Title'),
        'url': url,
        'duration': data.get('duration', 0),
        'stream_url': data['url'],
        'format_id': data.get('format_id', 'unknown'),
        'ext': data.get('ext', 'unknown'),
        'thumbnail': data.get('thumbnail'),
        'artist': artist
    }


async def fetch_playlist_songs(ytdl, url: str):
    """
    Extrae canciones de una playlist de YouTube

    Args:
        ytdl: Instancia de yt-dlp
        url: URL de la playlist

    Returns:
        Lista de tuplas (url, title, duration) de las canciones
    """
    try:
        data = ytdl.extract_info(url, download=False)
        songs = [
            (
                YOUTUBE_BASE_URL + 'watch?v=' + entry['id'],
                entry['title'],
                entry.get('duration', 0) or 0
            )
            for entry in data['entries']
            if entry is not None
        ]
        return songs
    except Exception as e:
        logging.error(f"Error fetching playlist songs: {e}")
        return []


def clean_video_url(url: str) -> str:
    """
    Limpia una URL de YouTube removiendo parámetros de playlist

    Args:
        url: URL del video (posiblemente con parámetros de playlist)

    Returns:
        URL limpia solo con el ID del video
    """
    if "watch?v=" in url and "&list=" in url:
        video_match = re.search(r'watch\?v=([^&]+)', url)
        if video_match:
            video_id = video_match.group(1)
            return f"https://www.youtube.com/watch?v={video_id}"
    return url


def is_youtube_url(url: str) -> bool:
    """Verifica si una URL es de YouTube"""
    return any(domain in url.lower() for domain in ['youtube.com', 'youtu.be', 'm.youtube.com'])


def is_playlist_url(url: str) -> bool:
    """Verifica si una URL es de una playlist de YouTube"""
    return "playlist?list=" in url or ("list=" in url and "watch?v=" not in url)


async def get_related_videos(url: str, limit: int = 15) -> list:
    """
    Extrae los videos relacionados de un video de YouTube.
    Intenta primero con related_videos, luego con YouTube Mix playlist.

    Args:
        url: URL del video de YouTube
        limit: Cantidad maxima de videos relacionados a retornar

    Returns:
        Lista de diccionarios con {id, title, duration, url}
    """
    # Extraer video_id de la URL
    video_id = None
    if 'watch?v=' in url:
        match = re.search(r'watch\?v=([^&]+)', url)
        if match:
            video_id = match.group(1)
    elif 'youtu.be/' in url:
        match = re.search(r'youtu\.be/([^?]+)', url)
        if match:
            video_id = match.group(1)

    if not video_id:
        logging.error("get_related_videos: No se pudo extraer video_id")
        return []

    related = []

    # Estrategia 1: Intentar obtener YouTube Mix playlist (RD + video_id)
    mix_url = f"https://www.youtube.com/watch?v={video_id}&list=RD{video_id}"
    logging.info(f"get_related_videos: Intentando Mix playlist: {mix_url}")
    related = await get_mix_playlist_videos(mix_url, video_id, limit)

    if related:
        logging.info(f"get_related_videos: Encontrados {len(related)} en Mix playlist")
        return related

    # Estrategia 2: Intentar con related_videos del video original
    related = await _get_related_from_video(url, limit)

    if related:
        logging.info(f"get_related_videos: Encontrados {len(related)} en related_videos")
        return related

    logging.info("get_related_videos: No se encontraron videos relacionados")
    return []


async def get_mix_playlist_videos(mix_url: str, original_video_id: str, limit: int) -> list:
    """
    Extrae videos de una YouTube Mix playlist.

    Args:
        mix_url: URL del mix (con list=RD...)
        original_video_id: ID del video original a excluir
        limit: Cantidad maxima de videos a retornar

    Returns:
        Lista de diccionarios con {id, title, duration, url}
    """
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,  # Flat para playlists es mas rapido
            'skip_download': True,
            'logger': YTDLLogger(),
            'playlistend': limit + 5,  # Extra por si filtramos algunos
        }

        loop = asyncio.get_event_loop()

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            data = await loop.run_in_executor(
                None,
                lambda: ydl.extract_info(mix_url, download=False)
            )

        if not data:
            return []

        related = []

        # Mix playlists tienen 'entries'
        entries = data.get('entries', [])
        for entry in entries:
            if not entry:
                continue

            entry_id = entry.get('id', '')

            # Saltar el video original
            if entry_id == original_video_id:
                continue

            related.append({
                'id': entry_id,
                'title': entry.get('title', ''),
                'duration': entry.get('duration', 0),
                'url': f"https://www.youtube.com/watch?v={entry_id}"
            })

            if len(related) >= limit:
                break

        return related

    except Exception as e:
        logging.debug(f"_get_mix_playlist_videos: Error: {e}")
        return []


async def _get_related_from_video(url: str, limit: int) -> list:
    """
    Intenta extraer related_videos del video usando EJS.
    """
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'skip_download': True,
            'logger': YTDLLogger(),
            # Habilitar todos los JS runtimes disponibles
            'extractor_args': {
                'youtube': {
                    'player_client': ['web'],
                }
            },
        }

        loop = asyncio.get_event_loop()

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            data = await loop.run_in_executor(
                None,
                lambda: ydl.extract_info(url, download=False)
            )

        if not data:
            return []

        related = []

        # Buscar en related_videos
        if 'related_videos' in data and data['related_videos']:
            for video in data['related_videos'][:limit]:
                if video and video.get('id'):
                    related.append({
                        'id': video.get('id'),
                        'title': video.get('title', ''),
                        'duration': video.get('duration', 0),
                        'url': f"https://www.youtube.com/watch?v={video.get('id')}"
                    })

        return related

    except Exception as e:
        logging.debug(f"_get_related_from_video: Error: {e}")
        return []
