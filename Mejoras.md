# Mejoras Propuestas para Music Maniac

## 🚀 Mejoras de Rendimiento

1. **Cache de metadatos de YouTube**
   - Actualmente se extrae metadata cada vez. Se podría cachear títulos y duraciones de canciones recientemente reproducidas
   - Reducir llamadas a yt-dlp guardando resultados por X tiempo

2. **Precarga de la siguiente canción**
   - Extraer el stream URL de la siguiente canción en la queue mientras la actual suena
   - Reducir tiempo de espera entre canciones

3. **Optimización de FFmpeg**
   - Los options de reconexión actuales están bien, pero se podría añadir `-probesize 32` y `-analyzeduration 0` para inicios más rápidos

4. **Async Spotify Playlist Processing**
   - Ya se usa asyncio.gather pero se podría añadir un límite de concurrencia para evitar rate limits

---

## ✨ Mejoras de Calidad/UX

1. **Sistema de favoritos por usuario**
   - `.favorite` para guardar la canción actual
   - `.favorites` para ver lista personal
   - Base de datos SQLite simple

2. **Historial de reproducción**
   - `.history` para ver últimas canciones reproducidas
   - Útil para "¿cómo se llamaba esa canción?"

3. ~~**Controles con botones (Discord UI)**~~ ✅
   - ~~Añadir botones de ⏸️ ▶️ ⏭️ 🔀 🔁 en el mensaje de nowplaying~~
   - ~~Similar al paginador actual~~

4. ~~**Mejoras en el comando queue**~~ ✅
   - ~~Mostrar duración total estimada de la queue~~
   - ~~Tiempo estimado hasta que toque cada canción~~

5. ~~**Comando de búsqueda mejorado**~~ ✅
   - ~~`.search <término>` que muestre 5 resultados con botones para elegir~~
   - ~~Más preciso que la búsqueda automática actual~~

6. **Letra de canciones**
   - Integración con API de Genius/Musixmatch
   - `.lyrics` para mostrar letra de canción actual

7. **Ecualizador/Filtros de audio**
   - Bass boost, nightcore, 8D audio usando filtros FFmpeg
   - `.filter <tipo>` para aplicar efectos

---

## 🎵 Nuevas Funcionalidades

1. **Queue persistente**
   - Guardar queue cuando el bot se desconecta
   - Recargar automáticamente al reconectar

2. **Playlists guardadas del servidor**
   - `.playlist save <nombre>` - Guardar queue actual
   - `.playlist load <nombre>` - Cargar playlist guardada
   - `.playlist list` - Ver playlists del servidor

3. **Sistema de votación para skip**
   - En servidores grandes, requerir X votos para skip
   - Configurable por servidor

4. **Comando de radio/autoplay**
   - Cuando queue termina, buscar canciones relacionadas automáticamente
   - Usar recomendaciones de YouTube/Spotify

5. **Estadísticas del servidor**
   - `.stats` - Canciones más reproducidas, usuario que más pone música, tiempo total escuchado

6. **Control de volumen**
   - `.volume <0-100>` para ajustar volumen por servidor
   - Actualmente está fijo en 0.375

7. **Integración con más plataformas**
   - SoundCloud, Apple Music, Bandcamp
   - `.source <youtube/spotify/soundcloud>` para forzar fuente

8. **Sistema de DJ Role**
   - Rol especial que tenga permisos para comandos administrativos (clear, stop, skipto)
   - Otros usuarios solo skip con votos

9. **Comando de remix/mashup**
   - Reproducir 2+ canciones simultáneamente mezcladas

10. **Comando de recommendations**
    - `.similar` - Recomendar canciones similares a la actual
    - Usar API de Spotify/Last.fm

---

## 🔧 Mejoras Técnicas/Mantenimiento

1. **Migrar a Slash Commands (Application Commands)**
   - Más modernos que prefix commands
   - Mejor UX con autocompletado

2. **Sistema de configuración por servidor**
   - Prefix customizable
   - Idioma (EN/ES)
   - Timeout de desconexión configurable

3. **Manejo de errores mejorado**
   - Reintentos automáticos cuando yt-dlp falla
   - Fallback a diferentes formatos si uno falla

4. **Rate limiting de comandos**
   - Evitar spam de comandos (`.skip` 10 veces)
