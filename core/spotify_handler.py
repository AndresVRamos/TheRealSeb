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
        Tupla (youtube_url, track_name, duration_seconds) o (None, None, 0) si falla
    """
    try:
        track = sp.track(track_id)
        track_name = track['name']
        artist_name = track['artists'][0]['name']
        duration_seconds = track.get('duration_ms', 0) // 1000
        search_query = f"{track_name} {artist_name}"
        query_string = urllib.parse.urlencode({'search_query': search_query})

        async with session.get(YOUTUBE_RESULTS_URL + query_string) as response:
            content = await response.text()
            search_results = re.findall(r'/watch\?v=(.{11})', content)
            if not search_results:
                logging.error("No se encontraron resultados en YouTube para el track de Spotify.")
                return None, None, 0
            youtube_url = YOUTUBE_BASE_URL + 'watch?v=' + search_results[0]
            youtube_url_cache[track['id']] = youtube_url
            return youtube_url, track_name, duration_seconds
    except Exception as e:
        logging.error(f"Error fetching YouTube URL from Spotify track: {e}")
        return None, None, 0


async def fetch_spotify_playlist_tracks(sp, spotify_url: str) -> list:
    """
    Extrae los tracks de una playlist de Spotify y los convierte a URLs de YouTube

    Args:
        sp: Cliente de Spotify
        spotify_url: URL de la playlist de Spotify

    Returns:
        Lista de tuplas (youtube_url, track_name, duration_seconds)
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
                    duration_seconds = track.get('duration_ms', 0) // 1000
                    songs.append((youtube_url, track_name, duration_seconds))
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


async def search_spotify_track(sp, title: str, artist: str = None) -> dict:
    """
    Busca un track en Spotify por titulo y artista

    Args:
        sp: Cliente de Spotify
        title: Titulo de la cancion
        artist: Artista (opcional)

    Returns:
        Diccionario con info del track o None si no se encuentra
    """
    try:
        # Limpiar el titulo de caracteres especiales
        clean_title = re.sub(r'\([^)]*\)', '', title)
        clean_title = re.sub(r'\[[^\]]*\]', '', clean_title)
        clean_title = clean_title.strip()

        # Construir query
        if artist and artist.lower() not in ['unknown', 'desconocido', '', 'topic', 'vevo']:
            query = f"track:{clean_title} artist:{artist}"
        else:
            query = clean_title

        logging.info(f"Spotify: Buscando track con query: '{query}'")
        results = sp.search(q=query, type='track', limit=1)

        if results['tracks']['items']:
            track = results['tracks']['items'][0]
            logging.info(f"Spotify: Encontrado track: {track['name']} - {track['artists'][0]['name']}")
            return {
                'id': track['id'],
                'name': track['name'],
                'artist': track['artists'][0]['name'],
                'duration_ms': track['duration_ms']
            }

        logging.info(f"Spotify: No se encontro track para: {query}")
        return None

    except Exception as e:
        logging.error(f"Error buscando track en Spotify: {e}")
        return None


async def get_spotify_recommendations(sp, track_id: str, limit: int = 10) -> list:
    """
    Obtiene canciones relacionadas usando top tracks del artista y artistas relacionados.
    (El endpoint /recommendations fue deprecado para Client Credentials)

    Args:
        sp: Cliente de Spotify
        track_id: ID del track semilla
        limit: Cantidad de recomendaciones

    Returns:
        Lista de diccionarios con info de tracks recomendados
    """
    recommendations = []

    try:
        # Obtener info del track para saber el artista
        track_info = sp.track(track_id)
        artist_id = track_info['artists'][0]['id']
        artist_name = track_info['artists'][0]['name']
        current_track_name = track_info['name']

        logging.info(f"Spotify: Buscando canciones relacionadas para artista: {artist_name}")

        # Estrategia 1: Top tracks del mismo artista
        try:
            top_tracks = sp.artist_top_tracks(artist_id, country='US')
            for track in top_tracks['tracks'][:5]:
                # Evitar la misma canción
                if track['id'] != track_id:
                    recommendations.append({
                        'id': track['id'],
                        'name': track['name'],
                        'artist': track['artists'][0]['name'],
                        'duration_ms': track['duration_ms']
                    })
                    logging.info(f"Spotify: Top track: {track['name']} - {track['artists'][0]['name']}")
        except Exception as e:
            logging.warning(f"Spotify: Error obteniendo top tracks: {e}")

        # Estrategia 2: Artistas relacionados + sus top tracks
        try:
            related_artists = sp.artist_related_artists(artist_id)
            for artist in related_artists['artists'][:3]:
                related_top = sp.artist_top_tracks(artist['id'], country='US')
                for track in related_top['tracks'][:2]:
                    recommendations.append({
                        'id': track['id'],
                        'name': track['name'],
                        'artist': track['artists'][0]['name'],
                        'duration_ms': track['duration_ms']
                    })
                    logging.info(f"Spotify: Artista relacionado: {track['name']} - {track['artists'][0]['name']}")
        except Exception as e:
            logging.warning(f"Spotify: Error obteniendo artistas relacionados: {e}")

        return recommendations[:limit]

    except Exception as e:
        logging.error(f"Error obteniendo recomendaciones de Spotify: {e}")
        return []


async def get_youtube_url_for_track(track_name: str, artist_name: str) -> str:
    """
    Busca un track en YouTube dado nombre y artista

    Args:
        track_name: Nombre del track
        artist_name: Nombre del artista

    Returns:
        URL de YouTube o None
    """
    try:
        search_query = f"{track_name} {artist_name}"
        query_string = urllib.parse.urlencode({'search_query': search_query})

        async with aiohttp.ClientSession() as session:
            async with session.get(YOUTUBE_RESULTS_URL + query_string) as response:
                content = await response.text()
                search_results = re.findall(r'/watch\?v=(.{11})', content)
                if search_results:
                    return YOUTUBE_BASE_URL + 'watch?v=' + search_results[0]

        return None

    except Exception as e:
        logging.error(f"Error buscando en YouTube: {e}")
        return None
