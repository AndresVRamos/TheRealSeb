"""
Handler para obtener letras de canciones usando múltiples servicios con fallback.
Orden de prioridad: LRCLib -> Genius -> lyrics.ovh
"""

import aiohttp
import asyncio
import re
import logging
import os
from typing import Optional, Tuple


def clean_song_title(title: str) -> Tuple[str, str]:
    """
    Limpia el título del video de YouTube para extraer artista y título.
    Retorna (artista, titulo) o (titulo, "") si no se puede separar.
    """
    # Remover texto entre paréntesis/corchetes comunes
    patterns_to_remove = [
        r'\(Official\s*(Music\s*)?Video\)',
        r'\(Official\s*Audio\)',
        r'\(Lyric\s*Video\)',
        r'\(Lyrics\)',
        r'\(Audio\)',
        r'\(Visualizer\)',
        r'\(HD\)',
        r'\(HQ\)',
        r'\[Official\s*(Music\s*)?Video\]',
        r'\[Official\s*Audio\]',
        r'\[Lyric\s*Video\]',
        r'\[Lyrics\]',
        r'\[Audio\]',
        r'\[HD\]',
        r'\[HQ\]',
        r'ft\.\s*[\w\s]+',
        r'feat\.\s*[\w\s]+',
        r'\|.*$',
    ]

    cleaned = title
    for pattern in patterns_to_remove:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)

    cleaned = cleaned.strip()

    # Intentar separar artista - título
    separators = [' - ', ' – ', ' — ', ' ~ ']
    for sep in separators:
        if sep in cleaned:
            parts = cleaned.split(sep, 1)
            if len(parts) == 2:
                return parts[0].strip(), parts[1].strip()

    return cleaned, ""


async def fetch_lyrics_lrclib(title: str, artist: str = "") -> Optional[dict]:
    """
    Obtiene letras de LRCLib (con timestamps si están disponibles).
    Retorna dict con 'plain' y/o 'synced' lyrics, o None si no encuentra.
    """
    try:
        base_url = "https://lrclib.net/api/search"

        # Construir query
        query = f"{artist} {title}".strip() if artist else title

        async with aiohttp.ClientSession() as session:
            params = {"q": query}
            async with session.get(base_url, params=params, timeout=10) as response:
                if response.status != 200:
                    return None

                data = await response.json()

                if not data:
                    return None

                # Tomar el primer resultado
                result = data[0]

                lyrics_data = {
                    'source': 'LRCLib',
                    'artist': result.get('artistName', artist),
                    'title': result.get('trackName', title),
                    'plain': result.get('plainLyrics'),
                    'synced': result.get('syncedLyrics'),
                    'duration': result.get('duration')
                }

                # Solo retornar si hay letras
                if lyrics_data['plain'] or lyrics_data['synced']:
                    return lyrics_data

                return None

    except asyncio.TimeoutError:
        logging.warning("LRCLib timeout")
        return None
    except Exception as e:
        logging.error(f"Error fetching from LRCLib: {e}")
        return None


async def fetch_lyrics_genius(title: str, artist: str = "", api_key: str = None) -> Optional[dict]:
    """
    Obtiene letras de Genius usando la librería lyricsgenius.
    Requiere GENIUS_API_KEY en variables de entorno.
    """
    if not api_key:
        api_key = os.getenv('GENIUS_API_KEY')

    if not api_key:
        logging.warning("GENIUS_API_KEY no configurada")
        return None

    try:
        import lyricsgenius

        # Ejecutar en thread pool porque lyricsgenius no es async
        loop = asyncio.get_event_loop()

        def search_genius():
            genius = lyricsgenius.Genius(api_key, verbose=False, remove_section_headers=True)
            genius.timeout = 10

            # Buscar canción
            query = f"{artist} {title}".strip() if artist else title
            song = genius.search_song(title, artist if artist else None)

            if song:
                return {
                    'source': 'Genius',
                    'artist': song.artist,
                    'title': song.title,
                    'plain': song.lyrics,
                    'synced': None,
                    'url': song.url
                }
            return None

        result = await loop.run_in_executor(None, search_genius)
        return result

    except ImportError:
        logging.error("lyricsgenius no está instalado")
        return None
    except Exception as e:
        logging.error(f"Error fetching from Genius: {e}")
        return None


async def fetch_lyrics_ovh(title: str, artist: str = "") -> Optional[dict]:
    """
    Obtiene letras de lyrics.ovh (API simple y gratuita).
    """
    if not artist:
        # lyrics.ovh requiere artista y título separados
        # Intentar extraer del título si no se proporciona
        return None

    try:
        base_url = f"https://api.lyrics.ovh/v1/{artist}/{title}"

        async with aiohttp.ClientSession() as session:
            async with session.get(base_url, timeout=10) as response:
                if response.status != 200:
                    return None

                data = await response.json()

                if 'lyrics' in data and data['lyrics']:
                    return {
                        'source': 'lyrics.ovh',
                        'artist': artist,
                        'title': title,
                        'plain': data['lyrics'],
                        'synced': None
                    }

                return None

    except asyncio.TimeoutError:
        logging.warning("lyrics.ovh timeout")
        return None
    except Exception as e:
        logging.error(f"Error fetching from lyrics.ovh: {e}")
        return None


async def get_lyrics(song_title: str, genius_api_key: str = None) -> Optional[dict]:
    """
    Función principal que intenta obtener letras usando múltiples servicios.
    Orden: Genius -> LRCLib -> lyrics.ovh

    Retorna dict con:
    - source: nombre del servicio
    - artist: artista
    - title: título de la canción
    - plain: letras en texto plano
    - synced: letras sincronizadas (solo LRCLib, puede ser None)
    """
    # Limpiar y extraer artista/título
    artist, title = clean_song_title(song_title)

    if not title:
        title = artist
        artist = ""

    logging.info(f"Buscando letras para: '{artist}' - '{title}'")

    # 1. Intentar Genius (mejor cobertura)
    result = await fetch_lyrics_genius(title, artist, genius_api_key)
    if result:
        logging.info(f"Letras encontradas en Genius")
        return result

    # 2. Intentar LRCLib (tiene letras sincronizadas)
    result = await fetch_lyrics_lrclib(title, artist)
    if result:
        logging.info(f"Letras encontradas en LRCLib")
        return result

    # 3. Intentar lyrics.ovh (solo si tenemos artista)
    if artist:
        result = await fetch_lyrics_ovh(title, artist)
        if result:
            logging.info(f"Letras encontradas en lyrics.ovh")
            return result

    logging.info(f"No se encontraron letras para: {song_title}")
    return None


def parse_synced_lyrics(synced_lyrics: str) -> list:
    """
    Parsea letras sincronizadas en formato LRC.
    Retorna lista de tuplas (timestamp_seconds, line_text).
    """
    if not synced_lyrics:
        return []

    lines = []
    pattern = r'\[(\d{2}):(\d{2})\.(\d{2})\]\s*(.*)'

    for line in synced_lyrics.split('\n'):
        match = re.match(pattern, line)
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            centiseconds = int(match.group(3))
            text = match.group(4).strip()

            total_seconds = minutes * 60 + seconds + centiseconds / 100
            lines.append((total_seconds, text))

    return lines


def get_current_lyric_line(synced_lyrics: list, elapsed_seconds: float) -> Tuple[int, str]:
    """
    Encuentra la línea de letra actual basada en el tiempo transcurrido.
    Retorna (índice, texto de la línea).
    """
    if not synced_lyrics:
        return -1, ""

    current_index = -1
    current_text = ""

    for i, (timestamp, text) in enumerate(synced_lyrics):
        if timestamp <= elapsed_seconds:
            current_index = i
            current_text = text
        else:
            break

    return current_index, current_text


def format_lyrics_with_highlight(synced_lyrics: list, current_index: int, context_lines: int = 3) -> str:
    """
    Formatea las letras sincronizadas resaltando la línea actual.
    Muestra 'context_lines' líneas antes y después de la actual.
    """
    if not synced_lyrics or current_index < 0:
        return ""

    start = max(0, current_index - context_lines)
    end = min(len(synced_lyrics), current_index + context_lines + 1)

    lines = []
    for i in range(start, end):
        timestamp, text = synced_lyrics[i]
        if not text:
            continue
        if i == current_index:
            lines.append(f"**> {text}**")
        else:
            lines.append(f"  {text}")

    return "\n".join(lines)
