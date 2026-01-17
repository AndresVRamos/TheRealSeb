"""
Handler para integración con Spotify
"""
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import aiohttp
import urllib.parse
import re
import asyncio
import logging
from collections import defaultdict


YOUTUBE_BASE_URL = 'https://www.youtube.com/'
YOUTUBE_RESULTS_URL = 'https://www.youtube.com/results?'

# Cache para URLs de YouTube ya convertidas
youtube_url_cache = defaultdict(str)


def create_spotify_client(client_id: str, client_secret: str):
    """
    Crea un cliente de Spotify autenticado

    Args:
        client_id: ID de cliente de Spotify
        client_secret: Secret de cliente de Spotify

    Returns:
        Instancia de spotipy.Spotify
    """
    return spotipy.Spotify(auth_manager=SpotifyClientCredentials(
        client_id=client_id,
        client_secret=client_secret
    ))


def is_spotify_url(url: str) -> bool:
    """Verifica si una URL es de Spotify"""
    return "spotify.com" in url


def is_spotify_playlist(url: str) -> bool:
    """Verifica si una URL es de una playlist de Spotify"""
    return "spotify.com" in url and "playlist" in url


def is_spotify_track(url: str) -> bool:
    """Verifica si una URL es de un track de Spotify"""
    return "spotify.com" in url and "track" in url


async def get_youtube_url_from_spotify_track(sp, spotify_url: str) -> tuple:
    """
    Convierte una URL de track de Spotify a URL de YouTube

    Args:
        sp: Cliente de Spotify
        spotify_url: URL del track de Spotify

    Returns:
        Tupla (youtube_url, track_name) o (None, None) si falla
    """
    try:
        track_info = sp.track(spotify_url)
        track_name = track_info['name']
        artist_name = track_info['artists'][0]['name']
        search_query = f"{track_name} {artist_name}"
        query_string = urllib.parse.urlencode({'search_query': search_query})

        async with aiohttp.ClientSession() as session:
            async with session.get(YOUTUBE_RESULTS_URL + query_string) as response:
                content = await response.text()
                search_results = re.findall(r'/watch\?v=(.{11})', content)
                if not search_results:
                    logging.error("No se encontraron resultados en YouTube para la búsqueda.")
                    return None, None
                youtube_url = YOUTUBE_BASE_URL + 'watch?v=' + search_results[0]
                youtube_url_cache[track_info['id']] = youtube_url
                return youtube_url, track_name
    except Exception as e:
        logging.error(f"Error fetching YouTube URL from Spotify: {e}")
        return None, None


async def _get_youtube_url_from_track_id(sp, track_id: str, session) -> tuple:
    """
    Función auxiliar para convertir un track ID de Spotify a URL de YouTube

    Args:
        sp: Cliente de Spotify
        track_id: ID del track de Spotify
        session: Sesión de aiohttp

    Returns:
        Tupla (youtube_url, track_name) o (None, None) si falla
    """
    try:
        track = sp.track(track_id)
        track_name = track['name']
        artist_name = track['artists'][0]['name']
        search_query = f"{track_name} {artist_name}"
        query_string = urllib.parse.urlencode({'search_query': search_query})

        async with session.get(YOUTUBE_RESULTS_URL + query_string) as response:
            content = await response.text()
            search_results = re.findall(r'/watch\?v=(.{11})', content)
            if not search_results:
                logging.error("No se encontraron resultados en YouTube para el track de Spotify.")
                return None, None
            youtube_url = YOUTUBE_BASE_URL + 'watch?v=' + search_results[0]
            youtube_url_cache[track['id']] = youtube_url
            return youtube_url, track_name
    except Exception as e:
        logging.error(f"Error fetching YouTube URL from Spotify track: {e}")
        return None, None


async def fetch_spotify_playlist_tracks(sp, spotify_url: str) -> list:
    """
    Extrae los tracks de una playlist de Spotify y los convierte a URLs de YouTube

    Args:
        sp: Cliente de Spotify
        spotify_url: URL de la playlist de Spotify

    Returns:
        Lista de tuplas (youtube_url, track_name)
    """
    try:
        playlist_id = spotify_url.split("/")[-1].split("?")[0]
        results = sp.playlist_tracks(playlist_id)
        tracks = results['items']
        songs = []

        async with aiohttp.ClientSession() as session:
            tasks = []
            for item in tracks:
                track = item['track']
                if not track:
                    continue

                if track['id'] in youtube_url_cache:
                    youtube_url = youtube_url_cache[track['id']]
                    track_name = track['name']
                    songs.append((youtube_url, track_name))
                else:
                    tasks.append(_get_youtube_url_from_track_id(sp, track['id'], session))

            results = await asyncio.gather(*tasks)
            songs.extend([result for result in results if result[0]])

        return songs
    except Exception as e:
        logging.error(f"Error fetching Spotify playlist tracks: {e}")
        return []


def extract_track_id_from_url(url: str) -> str:
    """
    Extrae el ID del track de una URL de Spotify

    Args:
        url: URL del track de Spotify

    Returns:
        ID del track
    """
    return url.split("/")[-1].split("?")[0]
