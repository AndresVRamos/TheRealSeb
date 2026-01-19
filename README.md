# 🎵 TheRealSeb - Discord Music Bot

Bot de música para Discord con soporte para YouTube y Spotify, controles avanzados y GUI para logging integrada..

## ✨ Características

- 🎵 Reproducción desde YouTube y Spotify (canciones y playlists)
- ⏯️ Controles completos: play, pause, skip, seek, loop, shuffle
- 📋 Sistema de queue con paginación
- 🔍 Búsqueda automática por nombre
- 📊 Barra de progreso en tiempo real
- 🖥️ GUI con system tray para logs
- ⏱️ Auto-desconexión cuando está solo 5+ minutos
- 🎯 Comandos de posicionamiento (skipto, playnext, move)

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
```

4. Ejecuta el bot:
```bash
python maniac.py
```

## 🎮 Comandos

| Comando | Descripción |
|---------|-------------|
| `.play <enlace>` | Reproduce una canción o playlist |
| `.add <enlace>` | Añade a la queue |
| `.queue` | Muestra la queue actual |
| `.nowplaying` | Muestra la canción actual con barra de progreso |
| `.skip` | Salta la canción actual |
| `.skipto <posición>` | Salta a una posición específica |
| `.seek <tiempo>` | Salta a un timestamp (ej: 1m30s, 2:15) |
| `.pause` / `.resume` | Pausa/reanuda la reproducción |
| `.loop` | Activa/desactiva loop |
| `.shuffle` | Mezcla la queue |
| `.move <de> <a>` | Mueve una canción en la queue |
| `.clear` | Limpia la queue |
| `.stop` | Detiene y limpia todo |
| `.leave` | Desconecta el bot |
| `.commands` | Muestra todos los comandos |

## 🔧 Requisitos

- Python 3.8+
- FFmpeg (debe estar en PATH)
- Discord Bot Token
- Spotify API credentials (opcional, para soporte de Spotify)

## 📝 Próximas Mejoras

Ver [Mejoras.md](Mejoras.md) para la lista completa de features planeadas.

## 📄 Licencia

Este proyecto es de código abierto. Siéntete libre de usarlo y modificarlo.
