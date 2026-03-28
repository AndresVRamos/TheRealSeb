"""
Configuración centralizada del bot Music Maniac
Modifica estos valores para personalizar el comportamiento del bot
"""

# === TIMEOUTS ===
# Tiempo en segundos antes de desconectarse si el bot está solo en el canal de voz
ALONE_TIMEOUT_SECONDS = 60

# Timeout para conexión a canal de voz (segundos)
VOICE_CONNECT_TIMEOUT = 60.0

# Timeout de las vistas interactivas (segundos)
QUEUE_VIEW_TIMEOUT = 180
MUSIC_CONTROLS_TIMEOUT = 180
SEARCH_VIEW_TIMEOUT = 60

# === QUEUE ===
# Cantidad de canciones por página en el comando .queue
QUEUE_ITEMS_PER_PAGE = 25

# === REPRODUCTOR ===
# Volumen de reproducción (0.0 a 1.0)
PLAYBACK_VOLUME = 0.375

# Intervalo de actualización del embed nowplaying (segundos)
NOWPLAYING_UPDATE_INTERVAL = 15

# Longitud de la barra de progreso (cantidad de caracteres)
PROGRESS_BAR_LENGTH = 15

# Caracteres de la barra de progreso
PROGRESS_BAR_FILLED = "■"
PROGRESS_BAR_EMPTY = "─"

# === BÚSQUEDA ===
# Cantidad de resultados en el comando .search
SEARCH_MAX_RESULTS = 5

# === ESTADÍSTICAS ===
# Ruta de la base de datos SQLite para estadísticas
STATS_DATABASE_PATH = "data/stats.db"

# Cantidad de canciones en el comando .topsongs
TOP_SONGS_LIMIT = 10

# Cantidad de usuarios en el comando .topusers
TOP_USERS_LIMIT = 5

# Cantidad de canciones top del usuario en .stats y .mystats
USER_TOP_SONGS_LIMIT = 5

# Cantidad de canciones en el historial (.history)
HISTORY_LIMIT = 10

# === WRAPPED ===
# Habilitar o deshabilitar el módulo Wrapped (comandos .wrapped, .ws, etc.)
WRAPPED_ENABLED = True

# Año mínimo para estadísticas Wrapped
WRAPPED_MIN_YEAR = 2020

# Cantidad de canciones en el top de Wrapped
WRAPPED_TOP_TRACKS_LIMIT = 5

# Cantidad de artistas en el top de Wrapped
WRAPPED_TOP_ARTISTS_LIMIT = 5

# === PERSONALIDAD MUSICAL ===
# Umbrales para validar que la hora favorita sea significativa
# para asignar personalidades como "Night Owl" o "Early Bird"
PERSONALITY_MIN_HOUR_PLAYS = 10       # Mínimo de reproducciones en la hora favorita
PERSONALITY_MIN_HOUR_PERCENTAGE = 0.20  # Porcentaje mínimo del total (20%)

# Umbrales para asignación de personalidades
DEVOTED_FAN_THRESHOLD = 0.4      # >40% del mismo artista = Devoted Fan
EXPLORER_THRESHOLD = 0.8         # >80% canciones únicas = Explorer
LOYALIST_THRESHOLD = 0.3         # <30% variedad = Loyalist
SPECIALIST_MAX_ARTISTS = 5       # <5 artistas diferentes = Specialist
ENTHUSIAST_MIN_PLAYS = 100       # >100 reproducciones = Music Enthusiast

# === LETRAS ===
# Timeout para APIs de letras (segundos)
LYRICS_API_TIMEOUT = 10
# Umbral de similitud para coincidencia de artista
LYRICS_ARTIST_SIMILARITY = 0.3

# === COLORES DE EMBEDS ===
# Color verde de Spotify (RGB)
SPOTIFY_GREEN_RGB = (30, 215, 96)

# === OTROS TIMEOUTS ===
# Timeout para esperar resultados de futures (segundos)
FUTURE_RESULT_TIMEOUT = 5
