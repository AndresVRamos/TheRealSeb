# 🎵 TheRealSeb - Discord Music Bot

Bot de música para Discord con soporte para YouTube y Spotify, controles avanzados y GUI para logging integrada..

## ✨ Características

- 🎵 Reproducción desde YouTube y Spotify (canciones y playlists)
- ⏯️ Controles completos: play, pause, skip, seek, loop, shuffle
- 📻 Radio/Autoplay: reproduce canciones relacionadas automáticamente cuando termina la queue
- 📋 Sistema de queue con paginación
- 🔍 Búsqueda automática por nombre
- 📊 Barra de progreso en tiempo real
- 📝 Búsqueda de letras con múltiples fuentes (Genius, LRCLib, lyrics.ovh)
- 🖥️ GUI con system tray para logs
- 🌐 Web Dashboard para monitoreo en tiempo real
- ⏱️ Auto-desconexión cuando el bot está solo en el canal de voz
- 🎯 Comandos de posicionamiento (skipto, playnext, move, remove)
- 🚀 Soporte completo para **Slash Commands** de Discord (`/comando`)

## 📦 Instalación

### Windows (Automático)

1. Clona el repositorio:
```bash
git clone https://github.com/AndresVRamos/TheRealSeb
cd TheRealSeb
```

2. Ejecuta el instalador:
```
Setup\Windows\install.bat
```

El instalador automáticamente:
- Verifica e instala Python (via winget si es necesario)
- Verifica e instala FFmpeg (via winget si es necesario)
- Instala las dependencias de Python
- Crea el archivo `.env` desde `.env.example`
- Ofrece opciones para iniciar el bot y/o agregarlo al inicio de Windows

#### Scripts adicionales

| Script | Descripción |
|--------|-------------|
| `Setup\Windows\start.bat` | Inicia el bot en segundo plano |
| `Setup\Windows\add-to-startup.bat` | Agrega el bot al inicio de Windows |
| `Setup\Windows\remove-from-startup.bat` | Remueve el bot del inicio de Windows |

### Linux (Automático)

1. Clona el repositorio:
```bash
git clone https://github.com/AndresVRamos/TheRealSeb
cd TheRealSeb
```

2. Ejecuta el instalador:
```bash
chmod +x Setup/Linux/install.sh
./Setup/Linux/install.sh
```

El instalador detecta automáticamente tu gestor de paquetes (apt, dnf, pacman, zypper) e instala Python, FFmpeg y las dependencias.

#### Scripts adicionales

| Script | Descripción |
|--------|-------------|
| `Setup/Linux/start.sh` | Inicia el bot en segundo plano |
| `Setup/Linux/add-to-startup.sh` | Agrega el bot al inicio del sistema (systemd) |
| `Setup/Linux/remove-from-startup.sh` | Remueve el bot del inicio del sistema |

### macOS (Automático)

1. Clona el repositorio:
```bash
git clone https://github.com/AndresVRamos/TheRealSeb
cd TheRealSeb
```

2. Ejecuta el instalador:
```bash
chmod +x Setup/Mac/install.sh
./Setup/Mac/install.sh
```

El instalador verifica e instala Homebrew, Python, FFmpeg y las dependencias automáticamente.

#### Scripts adicionales

| Script | Descripción |
|--------|-------------|
| `Setup/Mac/start.sh` | Inicia el bot |
| `Setup/Mac/add-to-startup.sh` | Agrega el bot al inicio del sistema (launchd) |
| `Setup/Mac/remove-from-startup.sh` | Remueve el bot del inicio del sistema |

### Manual

1. Clona el repositorio:
```bash
git clone https://github.com/AndresVRamos/TheRealSeb
cd TheRealSeb
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

> **Cómo obtener las credenciales:**
> - **Discord (obligatorio):** Crea una aplicación en [discord.com/developers/applications](https://discord.com/developers/applications), ve a "Bot" y copia el token
> - **Spotify (opcional):** Obtén credenciales gratis en [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard)
> - **Genius (opcional):** Obtén una API key gratis en [genius.com/api-clients](https://genius.com/api-clients)

4. Ejecuta el bot:
```bash
python maniac.py
```

## 🎮 Comandos

> **Nota:** Todos los comandos están disponibles tanto con un prefijo custom establecido en el archivo config como a través de **Slash Commands** de Discord (`/comando`).

| Comando | Descripción |
|---------|-------------|
| `play <enlace>` | Reproduce una canción o playlist |
| `search <búsqueda>` | Busca una canción y muestra 5 opciones para escoger |
| `add <enlace>` | Añade a la queue |
| `playnext <enlace>` | Añade como siguiente canción |
| `queue` | Muestra la queue actual |
| `nowplaying` | Muestra la canción actual con barra de progreso |
| `lyrics [búsqueda]` | Muestra letras de la canción actual o búsqueda |
| `skip` | Salta la canción actual |
| `skipto <posición>` | Salta a una posición específica |
| `seek <tiempo>` | Salta a un timestamp (ej: 1m30s, 2:15) |
| `pause` / `resume` | Pausa/reanuda la reproducción |
| `loop` | Activa/desactiva loop |
| `autoplay` / `radio` | Activa/desactiva autoplay de canciones relacionadas |
| `shuffle` | Mezcla la queue |
| `move <de> <a>` | Mueve una canción en la queue |
| `remove <posición>` | Remueve una canción de la queue |
| `clear` | Limpia la queue |
| `stop` | Detiene y limpia todo |
| `leave` | Desconecta el bot |
| `help` | Muestra todos los comandos |

### Comandos de Estadísticas

| Comando | Descripción |
|---------|-------------|
| `mystats` | Muestra tus estadísticas en el servidor |
| `stats [@user]` | Muestra estadísticas de un usuario |
| `topsongs` | Top canciones del servidor |
| `topusers` | Top usuarios del servidor |
| `history [@user]` | Historial de reproducciones recientes |

### Comandos de Wrapped

| Comando | Descripción |
|---------|-------------|
| `wrapped [@user] [año]` | Resumen musical estilo Spotify Wrapped |
| `wrappedsummary` / `ws` | Resumen rápido del Wrapped |
| `topartists [@user] [año]` | Top artistas del año |
| `listeningtime` / `lt` | Tiempo total de escucha |
| `streak` | Racha de días consecutivos escuchando |

## 📝 Comando de Letras

El comando `lyrics` busca letras usando múltiples fuentes con sistema de fallback:

1. **Genius** - Mayor cobertura (requiere API key)
2. **LRCLib** - Incluye letras sincronizadas
3. **lyrics.ovh** - Fuente de respaldo

**Características:**
- Detecta automáticamente el artista del canal de YouTube
- Valida que los resultados coincidan con la canción buscada
- Soporta búsqueda de la canción actual o cualquier canción por nombre

**Uso:**
```
/lyrics              # Letras de la canción actual
/lyrics Bohemian Rhapsody   # Buscar letras específicas
```

## 🌐 Web Dashboard

El bot incluye un dashboard web para monitoreo en tiempo real con diseño Apple-style:

**Características:**
- 📝 Logs en tiempo real con Server-Sent Events (SSE)
- 🔍 Filtros por nivel (ERROR, WARNING, INFO, DEBUG)
- 📊 Estadísticas: total de líneas, errores, warnings
- 🎨 Diseño glassmorphism con modo oscuro/claro automático
- 📱 Responsive (desktop y móvil)

**Acceso:**
- Local: http://localhost:5000
- Remoto: http://TU_IP:5000
- System Tray: Click derecho en el icono → "Abrir Dashboard"

**Inicio automático:**
El dashboard se inicia automáticamente al ejecutar el bot con `main.pyw` o `maniac.py`.

Ver documentación completa en [gui/web/README.md](gui/web/README.md)

## 🔧 Requisitos

- Python 3.8+
- FFmpeg (debe estar en PATH)
- Discord Bot Token
- Spotify API credentials (opcional, para soporte de Spotify)

## 📊 Sistema de Estadísticas y Wrapped

El bot incluye un sistema de estadísticas con base de datos SQLite normalizada, diseñado para soportar funcionalidades de estadísticas de uso de usuarios.

> **Nota:** El módulo Wrapped está desactivado por defecto. Para habilitarlo, cambiar `WRAPPED_ENABLED = True` en `core/config.py`.

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
| **Night Owl** | Tu hora favorita es entre 6 PM - 4 AM (Noche/Madrugada) |
| **Early Bird** | Tu hora favorita es entre 5 AM - 11 AM (Mañana) |
| **Specialist** | Escuchas menos de 5 artistas diferentes |
| **Music Enthusiast** | Más de 100 reproducciones en el año |
| **Casual Listener** | No cumple ningún criterio especial |
| **Newcomer** | 0 reproducciones |

La evaluación se hace en orden de prioridad (Devoted Fan tiene mayor prioridad que Explorer, etc.).

> **Nota:** Para las personalidades basadas en hora (Night Owl, Early Bird), se requiere un mínimo de 10 reproducciones en esa hora favorita Y que represente al menos el 20% del total de reproducciones. Esto asegura que el patrón sea significativo.

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
The Real Seb/
├── maniac.py              # Punto de entrada principal
├── commands/
│   ├── music.py           # Comandos de música
│   └── wrapped.py         # Comandos de Wrapped
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
