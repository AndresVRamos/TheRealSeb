"""
Handler para búsqueda y extracción de URLs de YouTube
"""
import yt_dlp
import aiohttp
import urllib.parse
import re
import logging
import asyncio


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
    query_string = urllib.parse.urlencode({'search_query': query})
    async with aiohttp.ClientSession() as session:
        async with session.get(YOUTUBE_RESULTS_URL + query_string) as response:
            content = await response.text()
            search_results = re.findall(r'/watch\?v=(.{11})', content)
            if not search_results:
                logging.error("No se encontraron resultados en YouTube para la búsqueda.")
                return None
            return YOUTUBE_BASE_URL + 'watch?v=' + search_results[0]


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

    return {
        'title': data.get('title', 'Unknown Title'),
        'url': url,
        'duration': data.get('duration', 0),
        'stream_url': data['url'],
        'format_id': data.get('format_id', 'unknown'),
        'ext': data.get('ext', 'unknown'),
        'thumbnail': data.get('thumbnail')
    }


async def fetch_playlist_songs(ytdl, url: str):
    """
    Extrae canciones de una playlist de YouTube

    Args:
        ytdl: Instancia de yt-dlp
        url: URL de la playlist

    Returns:
        Lista de tuplas (url, title) de las canciones
    """
    try:
        data = ytdl.extract_info(url, download=False)
        songs = [(YOUTUBE_BASE_URL + 'watch?v=' + entry['id'], entry['title'])
                 for entry in data['entries']]
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
