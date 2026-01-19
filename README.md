# 🎵 TheRealSeb - Discord Music Bot

Bot de música para Discord con soporte para YouTube y Spotify, controles avanzados y GUI para logging integrada..

## ✨ Características

- 🎵 Reproducción desde YouTube y Spotify (canciones y playlists)
- ⏯️ Controles completos: play, pause, skip, seek, loop, shuffle
- 📋 Sistema de queue con paginación
- 🔍 Búsqueda automática por nombre
- 📊 Barra de progreso en tiempo real
- 📝 Búsqueda de letras con múltiples fuentes (Genius, LRCLib, lyrics.ovh)
- 🖥️ GUI con system tray para logs
- ⏱️ Auto-desconexión cuando está solo 5+ minutos
- 🎯 Comandos de posicionamiento (skipto, playnext, move, remove)

## 📦 Instalación

1. Clona el repositorio:
```bash
git clone https://github.com/TU-USUARIO/music-maniac-bot.git
cd music-maniac-bot
```

2. Instala las dependencias:
```bash
pip install -r requirements.txt
```

3. Crea un archivo `.env` con tus credenciales:
```env
discord_token=TU_TOKEN_DE_DISCORD
SPOTIPY_CLIENT_ID=TU_CLIENT_ID_DE_SPOTIFY
SPOTIPY_CLIENT_SECRET=TU_CLIENT_SECRET_DE_SPOTIFY
GENIUS_API_KEY=TU_API_KEY_DE_GENIUS
```

> **Nota:** La API de Genius es opcional pero mejora significativamente la búsqueda de letras. Puedes obtener una API key gratis en [genius.com/api-clients](https://genius.com/api-clients).

4. Ejecuta el bot:
```bash
python maniac.py
```

## 🎮 Comandos

| Comando | Descripción |
|---------|-------------|
| `.play <enlace>` | Reproduce una canción o playlist |
| `.add <enlace>` | Añade a la queue |
| `.playnext <enlace>` | Añade como siguiente canción |
| `.queue` | Muestra la queue actual |
| `.nowplaying` | Muestra la canción actual con barra de progreso |
| `.lyrics [búsqueda]` | Muestra letras de la canción actual o búsqueda |
| `.skip` | Salta la canción actual |
| `.skipto <posición>` | Salta a una posición específica |
| `.seek <tiempo>` | Salta a un timestamp (ej: 1m30s, 2:15) |
| `.pause` / `.resume` | Pausa/reanuda la reproducción |
| `.loop` | Activa/desactiva loop |
| `.shuffle` | Mezcla la queue |
| `.move <de> <a>` | Mueve una canción en la queue |
| `.remove <posición>` | Remueve una canción de la queue |
| `.clear` | Limpia la queue |
| `.stop` | Detiene y limpia todo |
| `.leave` | Desconecta el bot |
| `.help` | Muestra todos los comandos |

## 📝 Comando de Letras

El comando `.lyrics` busca letras usando múltiples fuentes con sistema de fallback:

1. **Genius** - Mayor cobertura (requiere API key)
2. **LRCLib** - Incluye letras sincronizadas
3. **lyrics.ovh** - Fuente de respaldo

**Características:**
- Detecta automáticamente el artista del canal de YouTube
- Valida que los resultados coincidan con la canción buscada
- Soporta búsqueda de la canción actual o cualquier canción por nombre

**Uso:**
```
.lyrics              # Letras de la canción actual
.lyrics Bohemian Rhapsody   # Buscar letras específicas
```

## 🔧 Requisitos

- Python 3.8+
- FFmpeg (debe estar en PATH)
- Discord Bot Token
- Spotify API credentials (opcional, para soporte de Spotify)

## 📝 Próximas Mejoras

Ver [Mejoras.md](Mejoras.md) para la lista completa de features planeadas.

## 📄 Licencia

Este proyecto es de código abierto. Siéntete libre de usarlo y modificarlo.
