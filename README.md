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
git clone https://github.com/AndresVRamos/TheRealSeb
cd therealseb
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
| `.search <búsqueda>` | Busca una canción y muestra 5 opciones para escoger |
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

### Comandos de Estadísticas

| Comando | Descripción |
|---------|-------------|
| `.mystats` | Muestra tus estadísticas en el servidor |
| `.stats [@user]` | Muestra estadísticas de un usuario |
| `.topsongs` | Top canciones del servidor |
| `.topusers` | Top usuarios del servidor |
| `.history [@user]` | Historial de reproducciones recientes |

### Comandos de Wrapped (Deshabilitados por defecto)

| Comando | Descripción |
|---------|-------------|
| `.wrapped [@user] [año]` | Resumen musical estilo Spotify Wrapped |
| `.wrappedsummary` / `.ws` | Resumen rápido del Wrapped |
| `.topartists [@user] [año]` | Top artistas del año |
| `.listeningtime` / `.lt` | Tiempo total de escucha |
| `.streak` | Racha de días consecutivos escuchando |

> Para habilitar los comandos de Wrapped, descomentar las líneas en `maniac.py`:
> ```python
> await bot.load_extension('commands.wrapped')
> logging.info("Cog de Wrapped cargado correctamente")
> ```

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

## 📊 Sistema de Estadísticas y Wrapped

El bot incluye un sistema de estadísticas con base de datos SQLite normalizada, diseñado para soportar funcionalidades de estadísticas de uso de usuarios.

La base de datos usa un esquema normalizado con las siguientes tablas:

**Tablas principales:**
- `users` - Usuarios de Discord con stats cacheadas
- `guilds` - Servidores con stats cacheadas
- `artists` - Artistas únicos normalizados
- `tracks` - Canciones únicas con YouTube/Spotify IDs
- `plays` - Cada reproducción con columnas generadas (year, month, hour, day_of_week)
- `listens` - Oyentes presentes por reproducción

**Tablas de agregación:**
- `daily_stats_user` - Stats diarias por usuario
- `monthly_stats_user` - Stats mensuales con top track/artist
- `yearly_stats_user` - Stats anuales para Wrapped
- `user_streaks` - Rachas de días consecutivos

### Personalidades Musicales

El sistema Wrapped asigna una "personalidad musical" basada en tus hábitos de escucha:

| Personalidad | Criterio |
|--------------|----------|
| **Devoted Fan** | >40% de tus plays son del mismo artista |
| **Explorer** | >80% de tus canciones son únicas (poca repetición) |
| **Loyalist** | <30% variedad (repites mucho las mismas canciones) |
| **Night Owl** | Tu hora favorita es entre 10 PM - 4 AM |
| **Early Bird** | Tu hora favorita es entre 5 AM - 9 AM |
| **Specialist** | Escuchas menos de 5 artistas diferentes |
| **Music Enthusiast** | Más de 100 reproducciones en el año |
| **Casual Listener** | No cumple ningún criterio especial |
| **Newcomer** | 0 reproducciones |

La evaluación se hace en orden de prioridad (Devoted Fan tiene mayor prioridad que Explorer, etc.).

### Funcionalidades Wrapped

1. **Top Canciones del Año** - Por cantidad de plays
2. **Top Artistas del Año** - Con tiempo total escuchado
3. **Hora Favorita** - Mañana/Tarde/Noche/Madrugada
4. **Día Favorito** - Lunes a Domingo
5. **Racha Más Larga** - Días consecutivos escuchando
6. **Primera Canción del Año** - Con timestamp
7. **Listening Personality** - Basada en los criterios anteriores
8. **Tiempo Total** - Horas/minutos escuchados
9. **Tracks Únicos** - Variedad de canciones
10. **Artistas Únicos** - Variedad de artistas

## 📁 Estructura del Proyecto

```
Music Maniac/
├── maniac.py              # Punto de entrada principal
├── commands/
│   ├── music.py           # Comandos de música
│   └── wrapped.py         # Comandos de Wrapped (deshabilitado)
├── core/
│   ├── config.py          # Configuración centralizada
│   ├── stats_handler.py   # Facade para estadísticas
│   ├── wrapped.py         # Generador de embeds Wrapped
│   ├── database/
│   │   ├── schema.py      # Esquema de base de datos v2
│   │   ├── queries.py     # Consultas optimizadas
│   │   └── migrations.py  # Migración de v1 a v2
│   └── ...
├── views/                 # Componentes UI de Discord
├── gui/                   # GUI de logging
└── data/
    └── stats.db           # Base de datos SQLite
```

## 📝 Próximas Mejoras

Ver [Mejoras.md](Mejoras.md) para la lista completa de features planeadas.
