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
# Año mínimo para estadísticas Wrapped
WRAPPED_MIN_YEAR = 2020

# Cantidad de canciones en el top de Wrapped
WRAPPED_TOP_TRACKS_LIMIT = 5

# Cantidad de artistas en el top de Wrapped
WRAPPED_TOP_ARTISTS_LIMIT = 5
