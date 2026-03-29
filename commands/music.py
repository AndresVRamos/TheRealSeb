"""
Cog de comandos de música
"""
import discord
from discord.ext import commands
import asyncio
import time
import logging

from core.config import (
    ALONE_TIMEOUT_SECONDS,
    VOICE_CONNECT_TIMEOUT,
    QUEUE_ITEMS_PER_PAGE,
    PLAYBACK_VOLUME,
    SEARCH_MAX_RESULTS,
    TOP_SONGS_LIMIT,
    TOP_USERS_LIMIT,
    USER_TOP_SONGS_LIMIT,
    HISTORY_LIMIT,
    FUTURE_RESULT_TIMEOUT,
    AUTOPLAY_ENABLED,
    AUTOPLAY_HISTORY_SIZE
)
from core.formatters import format_duration, parse_time_string
from core.playback import (
    pause_playback,
    resume_playback,
    skip_song,
    toggle_loop,
    toggle_autoplay,
    shuffle_queue,
    stop_playback
)
from core.autoplay_handler import get_related_song
from core.youtube_handler import (
    create_ytdl,
    search_youtube,
    search_youtube_multiple,
    extract_video_info,
    fetch_playlist_songs,
    clean_video_url,
    is_youtube_url,
    is_playlist_url
)
from core.spotify_handler import (
    create_spotify_client,
    is_spotify_url,
    is_spotify_playlist,
    is_spotify_track,
    get_youtube_url_from_spotify_track,
    fetch_spotify_playlist_tracks,
    extract_track_id_from_url
)
from views.queue_paginator import QueuePaginator
from views.music_controls import MusicControls, create_now_playing_embed
from views.search_results import SearchResultsView, create_search_embed
from core.presence import update_presence
from core.lyrics_handler import get_lyrics, parse_synced_lyrics, get_current_lyric_line, format_lyrics_with_highlight
from core.stats_handler import (
    init_database,
    record_play,
    get_user_stats,
    get_user_top_songs,
    get_server_top_users,
    get_server_top_songs,
    get_user_history
)


class MusicCommands(commands.Cog):
    """Cog con todos los comandos de música"""

    def __init__(self, bot, spotify_client_id: str, spotify_client_secret: str):
        self.bot = bot

        # Diccionarios de estado por servidor
        self.voice_clients = {}
        self.queues = {}
        self.song_data = {}
        self.loop_status = {}
        self.manual_stop = {}
        self.current_song = {}
        self.current_song_url = {}
        self.skipto_in_progress = {}
        self.seek_in_progress = {}
        self.alone_timeout_tasks = {}
        self.last_text_channel = {}
        self.active_controls_view = {}  # Vista de controles activa por servidor
        self.autoplay_status = {}  # Estado de autoplay por servidor
        self.autoplay_history = {}  # Historial de URLs para evitar repeticiones

        # Clientes externos
        self.ytdl = create_ytdl()
        self.sp = create_spotify_client(spotify_client_id, spotify_client_secret)

        # Inicializar base de datos de estadísticas
        init_database()

        # Opciones de FFmpeg
        self.ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': f'-vn -filter:a "volume={PLAYBACK_VOLUME}"'
        }

    async def disable_previous_controls(self, guild_id: int):
        """Deshabilita los controles del embed anterior si existe"""
        if guild_id in self.active_controls_view:
            old_view = self.active_controls_view[guild_id]
            try:
                old_view.cancel_update_loop()
                for item in old_view.children:
                    item.disabled = True
                if old_view.message:
                    await old_view.message.edit(view=old_view)
            except Exception as e:
                logging.debug(f"No se pudo deshabilitar controles anteriores: {e}")
            del self.active_controls_view[guild_id]

    async def update_final_embed(self, guild_id: int):
        """Actualiza el embed con el estado final antes de cambiar de canción"""
        if guild_id not in self.active_controls_view:
            return

        view = self.active_controls_view[guild_id]
        if not view.message:
            return

        try:
            view.cancel_update_loop()

            song_finished = False
            if guild_id in self.song_data:
                data = self.song_data[guild_id]
                elapsed_time = (time.time() - data['start_time']) - data['paused_time']
                if data['pause_start_time'] > 0:
                    elapsed_time -= (time.time() - data['pause_start_time'])
                if data['duration'] - elapsed_time < 2:
                    song_finished = True

            embed = create_now_playing_embed(
                self.song_data, self.queues, self.loop_status,
                guild_id, song_finished=song_finished
            )

            for item in view.children:
                item.disabled = True

            await view.message.edit(embed=embed, view=view)
        except Exception as e:
            logging.debug(f"No se pudo actualizar embed final: {e}")

    async def ensure_voice(self, ctx) -> bool:
        """Verifica que el usuario esté en un canal de voz y conecta el bot si es necesario"""
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("🚫 **Debes estar en un canal de voz para usar este comando.**")
            return False

        guild_id = ctx.guild.id

        # Verificar si ya existe una conexión de voz a nivel del bot (no solo en nuestro diccionario)
        existing_vc = ctx.guild.voice_client

        if existing_vc:
            # Ya hay una conexión existente
            if existing_vc.is_connected():
                # Si está conectado, actualizar nuestro diccionario y reutilizar
                self.voice_clients[guild_id] = existing_vc
                logging.info(f"Reutilizando conexión existente en: {existing_vc.channel}")
                return True
            else:
                # Si no está conectado, limpiar la sesión zombie
                logging.info("Limpiando sesión de voz zombie...")
                try:
                    await existing_vc.disconnect(force=True)
                except Exception as e:
                    logging.debug(f"Error desconectando sesión zombie: {e}")
                if guild_id in self.voice_clients:
                    del self.voice_clients[guild_id]

        # Limpiar entrada en nuestro diccionario si existe pero no es válida
        if guild_id in self.voice_clients:
            try:
                if not self.voice_clients[guild_id].is_connected():
                    del self.voice_clients[guild_id]
            except Exception:
                del self.voice_clients[guild_id]

        # Intentar conectar
        if guild_id not in self.voice_clients:
            try:
                logging.info(f"Intentando conectarse al canal de voz: {ctx.author.voice.channel}")
                voice_client = await ctx.author.voice.channel.connect(timeout=VOICE_CONNECT_TIMEOUT)
                self.voice_clients[guild_id] = voice_client
                logging.info(f"Conectado a: {ctx.author.voice.channel}")

                # Esperar a que la conexión esté completamente establecida
                for _ in range(10):  # Máximo 2 segundos
                    if voice_client.is_connected():
                        break
                    await asyncio.sleep(0.2)

                if not voice_client.is_connected():
                    logging.error("La conexión de voz no se estabilizó")
                    await ctx.send("⚠️ **La conexión de voz no se pudo estabilizar. Intenta de nuevo.**")
                    if guild_id in self.voice_clients:
                        del self.voice_clients[guild_id]
                    return False

            except Exception as e:
                logging.error(f"Error al conectar al canal de voz: {e}")
                await ctx.send(f"⚠️ **Error al conectar al canal de voz:** {e}")
                return False
        return True

    def after_play(self, ctx):
        """Callback que se ejecuta cuando termina una canción"""
        def _after_play(error):
            if error:
                logging.error(f"Error in after_play callback: {error}")
            else:
                logging.info(f"Song finished playing normally in guild {ctx.guild.id}")

            guild_id = ctx.guild.id
            if guild_id not in self.voice_clients or not self.voice_clients[guild_id].is_connected():
                logging.warning(f"Voice client not connected for guild {guild_id}")
                return

            # Registrar reproducción para todos los oyentes en el canal
            # Solo si la canción terminó normalmente (no por seek/skip/stop)
            is_seek = self.seek_in_progress.get(guild_id, False)
            is_skipto = self.skipto_in_progress.get(guild_id, False)
            is_manual_stop = self.manual_stop.get(guild_id, False)

            if not error and not is_seek and not is_skipto and not is_manual_stop:
                try:
                    if guild_id in self.song_data:
                        song_data = self.song_data[guild_id]
                        voice_channel = self.voice_clients[guild_id].channel
                        listeners = [(m.id, m.display_name) for m in voice_channel.members if not m.bot]
                        requester = song_data.get('requester')
                        guild = self.bot.get_guild(guild_id)

                        record_play(
                            guild_id=guild_id,
                            requester_id=requester.id if requester else 0,
                            requester_name=requester.display_name if requester else "Desconocido",
                            song_title=song_data['title'],
                            artist=song_data.get('artist'),
                            url=song_data.get('url'),
                            duration=song_data.get('duration', 0),
                            listeners=listeners,
                            guild_name=guild.name if guild else None,
                            thumbnail_url=song_data.get('thumbnail'),
                            guild_icon_url=str(guild.icon.url) if guild and guild.icon else None
                        )
                        logging.info(f"Recorded play for {len(listeners)} listeners in guild {guild_id}")
                except Exception as e:
                    logging.error(f"Error recording play stats: {e}")

            # Actualizar el embed con el estado final antes de cambiar de canción
            try:
                update_coro = self.update_final_embed(guild_id)
                update_fut = asyncio.run_coroutine_threadsafe(update_coro, self.bot.loop)
                update_fut.result(timeout=FUTURE_RESULT_TIMEOUT)  # Esperar máximo N segundos
            except Exception as e:
                logging.debug(f"Error actualizando embed final: {e}")

            if self.manual_stop.get(guild_id, False):
                logging.info(f"Manual stop detected for guild {guild_id}")
                self.manual_stop[guild_id] = False
                return

            logging.info(f"Calling play_next for guild {guild_id}")
            coro = self.play_next(ctx)
            fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
            try:
                fut.result()
            except Exception as e:
                logging.error(f"Error running play_next: {e}")

            

        return _after_play

    async def play_song(self, ctx, url: str, title: str = None, requester=None, is_autoplay=False):
        """Reproduce una canción"""
        try:
            guild_id = ctx.guild.id

            # Verificar que seguimos conectados antes de reproducir
            if guild_id not in self.voice_clients or not self.voice_clients[guild_id].is_connected():
                logging.warning("No conectado al intentar reproducir, reconectando...")
                if not await self.ensure_voice(ctx):
                    return

            logging.info(f"Attempting to play song: {url}")
            video_info = await extract_video_info(self.ytdl, url)

            if not video_info:
                raise Exception("No se pudo obtener el URL del stream")

            stream_url = video_info['stream_url']
            actual_title = title if title else video_info['title']

            logging.info(f"Stream URL obtained: {stream_url[:100]}...")
            logging.info(f"Format ID: {video_info['format_id']}")

            # Resetear la bandera manual_stop
            self.manual_stop[guild_id] = False

            # Guardar información de la canción actual
            self.current_song[guild_id] = actual_title
            self.current_song_url[guild_id] = url

            actual_requester = requester if requester else ctx.author

            self.song_data[guild_id] = {
                'title': actual_title,
                'url': url,
                'duration': video_info['duration'],
                'start_time': time.time(),
                'paused_time': 0,
                'pause_start_time': 0,
                'thumbnail': video_info.get('thumbnail'),
                'requester': actual_requester,
                'artist': video_info.get('artist'),
                'is_autoplay': is_autoplay
            }

            await update_presence(self.bot,True, actual_title)

            logging.info("Creating FFmpegOpusAudio player...")
            player = discord.FFmpegOpusAudio(stream_url, **self.ffmpeg_options)

            # Verificar conexión justo antes de reproducir
            if guild_id not in self.voice_clients or not self.voice_clients[guild_id].is_connected():
                logging.warning("Conexión perdida antes de reproducir, reconectando...")
                if not await self.ensure_voice(ctx):
                    return

            logging.info("Starting playback on voice client...")
            self.voice_clients[guild_id].play(player, after=self.after_play(ctx))

            await asyncio.sleep(0.5)

            if self.voice_clients[guild_id].is_playing():
                logging.info(f"Confirmed: Audio is playing for: {actual_title}")
            else:
                logging.error(f"Audio is NOT playing after start command for: {actual_title}")

            await self.disable_previous_controls(guild_id)

            # Crear embed y vista con controles
            embed = create_now_playing_embed(
                self.song_data, self.queues, self.loop_status,
                guild_id, ctx.author, autoplay_status=self.autoplay_status
            )

            view = MusicControls(
                ctx, None, self.voice_clients, self.loop_status,
                self.queues, self.song_data, self.manual_stop,
                bot=self.bot, autoplay_status=self.autoplay_status
            )

            message = await ctx.send(embed=embed, view=view)
            view.message = message
            view.update_button_states()
            await message.edit(view=view)

            # Guardar la vista activa
            self.active_controls_view[guild_id] = view
            view.start_update_loop()

        except Exception as e:
            logging.error(f"Error playing song: {e}")
            logging.error(f"Exception traceback:", exc_info=True)
            await ctx.send(f"⚠️ **Error al reproducir la canción:** {e}. Saltando a la siguiente...")
            await self.play_next(ctx)

    async def play_next(self, ctx, url: str = None):
        """Reproduce la siguiente canción en la queue"""
        guild_id = ctx.guild.id

        if guild_id in self.skipto_in_progress and self.skipto_in_progress[guild_id]:
            self.skipto_in_progress[guild_id] = False
            return

        if guild_id in self.seek_in_progress and self.seek_in_progress[guild_id]:
            self.seek_in_progress[guild_id] = False
            return

        if self.loop_status.get(guild_id, False):
            last_link = self.current_song_url.get(guild_id)
            last_title = self.current_song.get(guild_id)
            last_requester = self.song_data.get(guild_id, {}).get('requester')
            if last_link:
                logging.info(f"Looping song: {last_title}")
                await self.play_song(ctx, last_link, last_title, last_requester)
                return

        if url:
            logging.info(f"Playing next song: {url}")
            await self.play_song(ctx, url)
        elif self.queues.get(guild_id):
            song = self.queues[guild_id].pop(0)
            next_link = song[0]
            next_title = song[1]
            next_requester = song[2]
            logging.info(f"Playing next song from queue: {next_title}")
            await self.play_song(ctx, next_link, next_title, next_requester)
        else:
            # Verificar si autoplay está habilitado para este servidor
            if AUTOPLAY_ENABLED and self.autoplay_status.get(guild_id, False):
                await self._handle_autoplay(ctx, guild_id)
            else:
                logging.info("La queue está vacía, no hay nada que reproducir.")
                await update_presence(self.bot, False)
                await ctx.send("🚫 **La queue está vacía.**")

    async def _handle_autoplay(self, ctx, guild_id: int):
        """Busca y reproduce una cancion relacionada cuando autoplay está activo"""
        if guild_id not in self.song_data:
            logging.info("Autoplay: No hay datos de cancion anterior")
            await ctx.send("🚫 **La queue está vacía y no hay canción anterior para hacerle radio.**")
            await update_presence(self.bot, False)
            return

        current_song = self.song_data[guild_id]

        if guild_id not in self.autoplay_history:
            self.autoplay_history[guild_id] = set()

        if current_song.get('url'):
            self.autoplay_history[guild_id].add(current_song['url'])

        if len(self.autoplay_history[guild_id]) > AUTOPLAY_HISTORY_SIZE:
            history_list = list(self.autoplay_history[guild_id])
            self.autoplay_history[guild_id] = set(history_list[-AUTOPLAY_HISTORY_SIZE:])

        await ctx.send("🔄 **Autoplay:** Buscando canción relacionada...")

        try:
            related = await get_related_song(
                self.ytdl,
                current_song,
                self.autoplay_history[guild_id],
                self.sp
            )

            if related:
                url, title, duration = related
                logging.info(f"Autoplay: Encontrada cancion relacionada: {title}")

                self.autoplay_history[guild_id].add(url)

                await ctx.send(f"📻 **Autoplay:** *{title}*")
                # Usar el requester de la última canción real, no ctx.author
                last_requester = current_song.get('requester', ctx.author)
                await self.play_song(ctx, url, title, last_requester, is_autoplay=True)
            else:
                logging.info("Autoplay: No se encontró canción relacionada")
                await ctx.send("🚫 **Autoplay:** No se encontró canción relacionada.")
                await update_presence(self.bot, False)

        except Exception as e:
            logging.error(f"Error en autoplay: {e}")
            await ctx.send("⚠️ **Autoplay:** Error al buscar canción relacionada.")
            await update_presence(self.bot, False)

    async def alone_timeout(self, guild_id: int, channel):
        """Espera y desconecta el bot si sigue solo"""
        try:
            await asyncio.sleep(ALONE_TIMEOUT_SECONDS)

            if guild_id in self.voice_clients and self.voice_clients[guild_id].is_connected():
                voice_channel = self.voice_clients[guild_id].channel
                human_members = [member for member in voice_channel.members if not member.bot]

                if len(human_members) == 0:
                    logging.info(f"Bot estuvo solo por en {guild_id}, desconectando...")

                    try:
                        await channel.send("👋 Me quedé solo. Ya me voy 😔")
                    except Exception as e:
                        logging.error(f"Error al enviar mensaje de despedida: {e}")

                    self.manual_stop[guild_id] = True
                    if guild_id in self.active_controls_view:
                        self.active_controls_view[guild_id].cancel_update_loop()
                    self.voice_clients[guild_id].stop()
                    if guild_id in self.queues:
                        self.queues[guild_id].clear()

                    await self.voice_clients[guild_id].disconnect()
                    del self.voice_clients[guild_id]

                    await update_presence(self.bot,False)

                    if guild_id in self.alone_timeout_tasks:
                        del self.alone_timeout_tasks[guild_id]

        except asyncio.CancelledError:
            logging.info(f"Timeout cancelado para guild {guild_id} - alguien se unió al canal")
        except Exception as e:
            logging.error(f"Error en alone_timeout: {e}")

    # === LISTENERS ===

    @commands.Cog.listener()
    async def on_ready(self):
        """Actualizar presencia cuando el bot está listo"""
        await update_presence(self.bot,False)
        logging.info(f'{self.bot.user} is now jamming')

    @commands.Cog.listener()
    async def on_command(self, ctx):
        """Guardar el último canal de texto usado para cada servidor"""
        if ctx.guild:
            self.last_text_channel[ctx.guild.id] = ctx.channel

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Detecta cuando el bot se queda solo en el canal de voz"""
        try:
            guild_id = member.guild.id

            if guild_id not in self.voice_clients or not self.voice_clients[guild_id].is_connected():
                return

            voice_channel = self.voice_clients[guild_id].channel
            human_members = [m for m in voice_channel.members if not m.bot]

            if len(human_members) == 0:
                if guild_id not in self.alone_timeout_tasks or self.alone_timeout_tasks[guild_id].done():
                    logging.info(f"Bot quedó solo en guild {guild_id}, iniciando timeout de 5 minutos")

                    text_channel = self.last_text_channel.get(guild_id)
                    if not text_channel or text_channel not in member.guild.text_channels:
                        text_channel = member.guild.text_channels[0] if member.guild.text_channels else None

                    if text_channel:
                        task = asyncio.create_task(self.alone_timeout(guild_id, text_channel))
                        self.alone_timeout_tasks[guild_id] = task
            else:
                if guild_id in self.alone_timeout_tasks and not self.alone_timeout_tasks[guild_id].done():
                    logging.info(f"Alguien se unió al canal en guild {guild_id}, cancelando timeout")
                    self.alone_timeout_tasks[guild_id].cancel()
                    del self.alone_timeout_tasks[guild_id]

        except Exception as e:
            logging.error(f"Error en on_voice_state_update: {e}")

    # === COMANDOS ===

    @commands.command(name="play", help="Reproduce una canción o playlist desde YouTube o Spotify.")
    async def play(self, ctx, *, url: str):
        if not await self.ensure_voice(ctx):
            return

        guild_id = ctx.guild.id
        if guild_id not in self.queues:
            self.queues[guild_id] = []

        if guild_id in self.voice_clients and (
            self.voice_clients[guild_id].is_playing() or
            self.voice_clients[guild_id].is_paused()
        ):
            await self.add(ctx, url=url)
            return

        try:
            if is_spotify_url(url):
                if is_spotify_playlist(url):
                    await ctx.send("🔍 **Procesando playlist de Spotify...** Esto puede tardar un momento.")
                    songs = await fetch_spotify_playlist_tracks(self.sp, url)
                    if not songs:
                        await ctx.send("🚫 **La playlist de Spotify está vacía o no se pudo procesar.**")
                        return
                    first_song_url, first_title, _ = songs[0]
                    songs_with_requester = [(song[0], song[1], ctx.author, song[2]) for song in songs[1:]] #(url, titulo, requester, duracion)
                    self.queues[guild_id].extend(songs_with_requester)
                    await self.play_song(ctx, first_song_url, first_title, ctx.author)
                    await ctx.send(f"➕ **Añadida la playlist a la queue:** {len(songs)} canciones")
                    return

                elif is_spotify_track(url):
                    yt_link, _ = await get_youtube_url_from_spotify_track(self.sp, url)
                    if not yt_link:
                        await ctx.send("⚠️ **Error al obtener el enlace de YouTube desde Spotify.**")
                        return
                    url = yt_link

            if is_playlist_url(url):
                songs = await fetch_playlist_songs(self.ytdl, url)
                if not songs:
                    await ctx.send("🚫 **La playlist de YouTube está vacía.**")
                    return
                first_song_url, first_title, _ = songs[0]
                # Añadir con duración de la playlist
                songs_with_requester = [(song[0], song[1], ctx.author, song[2]) for song in songs[1:]]
                self.queues[guild_id].extend(songs_with_requester)
                await ctx.send(f"➕ **Añadida la playlist a la queue:** {len(songs)} canciones")
                await self.play_song(ctx, first_song_url, first_title, ctx.author)
            else:
                if not is_youtube_url(url):
                    url = await search_youtube(url)
                    if not url:
                        await ctx.send("⚠️ **No se encontró ningún resultado en YouTube.**")
                        return
                else:
                    url = clean_video_url(url)

                await self.play_song(ctx, url)

        except Exception as e:
            logging.error(f"Error al reproducir la canción: {e}")
            await ctx.send(f"⚠️ **Error al reproducir la canción:** {e}")

    @commands.command(name="add", help="Añade una canción o playlist a la queue.")
    async def add(self, ctx, *, url: str):
        if not await self.ensure_voice(ctx):
            return

        guild_id = ctx.guild.id
        if guild_id not in self.queues:
            self.queues[guild_id] = []

        try:
            if is_spotify_url(url):
                if is_spotify_playlist(url):
                    await ctx.send("🔍 **Procesando playlist de Spotify...** Esto puede tardar un momento.")
                    songs = await fetch_spotify_playlist_tracks(self.sp, url)
                    if not songs:
                        await ctx.send("🚫 **La playlist de Spotify está vacía o no se pudo procesar.**")
                        return
                    # Añadir con duración de Spotify
                    songs_with_requester = [(song[0], song[1], ctx.author, song[2]) for song in songs]
                    self.queues[guild_id].extend(songs_with_requester)
                    await ctx.send(f"➕ **Añadida la playlist a la queue:** {len(songs)} canciones")
                    return
                else:
                    track_id = extract_track_id_from_url(url)
                    yt_link, title = await get_youtube_url_from_spotify_track(self.sp, url)
                    if not yt_link:
                        await ctx.send("⚠️ **Error al obtener el enlace de YouTube desde Spotify.**")
                        return
                    # Obtener duración del video de YouTube
                    video_info = await extract_video_info(self.ytdl, yt_link)
                    duration = video_info.get('duration', 0) if video_info else 0
                    self.queues[guild_id].append((yt_link, title, ctx.author, duration))
                    await ctx.send(f"➕ **Añadida a la queue:** *{title}*")
                    return

            if is_playlist_url(url):
                songs = await fetch_playlist_songs(self.ytdl, url)
                if not songs:
                    await ctx.send("🚫 **La playlist de YouTube está vacía.**")
                    return
                # Añadir con duración de la playlist
                songs_with_requester = [(song[0], song[1], ctx.author, song[2]) for song in songs]
                self.queues[guild_id].extend(songs_with_requester)
                await ctx.send(f"➕ **Añadida la playlist a la queue:** {len(songs)} canciones")
            else:
                if not is_youtube_url(url):
                    url = await search_youtube(url)
                    if not url:
                        await ctx.send("⚠️ **No se encontró ningún resultado en YouTube.**")
                        return

                video_info = await extract_video_info(self.ytdl, url)
                title = video_info['title']
                duration = video_info.get('duration', 0)
                self.queues[guild_id].append((url, title, ctx.author, duration))
                await ctx.send(f"➕ **Añadida a la queue:** *{title}*")

        except Exception as e:
            logging.error(f"Error añadiendo canción a la queue: {e}")
            await ctx.send(f"⚠️ **Error al añadir la canción a la queue:** {e}")

    @commands.command(name="queue", help="Muestra la queue actual.")
    async def show_queue(self, ctx):
        guild_id = ctx.guild.id

        if guild_id not in self.queues or not self.queues[guild_id]:
            await ctx.send("🚫 **La queue está vacía!**")
            return

        items_per_page = QUEUE_ITEMS_PER_PAGE
        total_songs = len(self.queues[guild_id])
        pages = [self.queues[guild_id][i:i + items_per_page]
                 for i in range(0, len(self.queues[guild_id]), items_per_page)]

        # Calcular tiempo restante de la canción actual
        current_song_remaining = 0
        if guild_id in self.song_data and guild_id in self.voice_clients:
            if self.voice_clients[guild_id].is_playing() or self.voice_clients[guild_id].is_paused():
                data = self.song_data[guild_id]
                elapsed_time = (time.time() - data['start_time']) - data['paused_time']
                if data['pause_start_time'] > 0:
                    elapsed_time -= (time.time() - data['pause_start_time'])
                current_song_remaining = max(0, data['duration'] - elapsed_time)

        # Calcular duración total de la queue (solo canciones con duración conocida)
        total_duration = sum(
            song[3] if len(song) > 3 and song[3] else 0
            for song in self.queues[guild_id]
        )

        paginator = QueuePaginator(
            ctx, pages, total_songs, items_per_page,
            current_song_remaining=current_song_remaining,
            total_duration=total_duration
        )
        paginator.children[0].disabled = True
        if len(pages) <= 1:
            paginator.children[1].disabled = True

        initial_embed = paginator.create_embed()
        await ctx.send(embed=initial_embed, view=paginator)

    @commands.command(name="playnext", help="Agrega la canción a la siguiente posición en la queue.")
    async def playnext(self, ctx, *, url: str):
        if not await self.ensure_voice(ctx):
            return

        guild_id = ctx.guild.id
        if guild_id not in self.queues:
            self.queues[guild_id] = []

        is_playing = (guild_id in self.voice_clients and
                      (self.voice_clients[guild_id].is_playing() or
                       self.voice_clients[guild_id].is_paused()))

        try:
            if is_spotify_url(url):
                if is_spotify_playlist(url):
                    songs = await fetch_spotify_playlist_tracks(self.sp, url)
                    if not songs:
                        await ctx.send("🚫 **La playlist de Spotify está vacía.**")
                        return

                    if not is_playing:
                        # Reproducir la primera canción directamente
                        first_song_url, first_title, _ = songs[0]
                        songs_with_requester = [(song[0], song[1], ctx.author, song[2]) for song in songs[1:]]
                        self.queues[guild_id].extend(songs_with_requester)
                        await self.play_song(ctx, first_song_url, first_title, ctx.author)
                        await ctx.send(f"➕ **Añadida la playlist a la queue:** {len(songs)} canciones")
                    else:
                        for song in reversed(songs):
                            self.queues[guild_id].insert(0, (song[0], song[1], ctx.author, song[2]))
                        await ctx.send(f"➕ **Añadida la playlist a la posición siguiente:** {len(songs)} canciones")
                    return
                else:
                    yt_link, title = await get_youtube_url_from_spotify_track(self.sp, url)
                    if not yt_link:
                        await ctx.send("⚠️ **Error al obtener el enlace de YouTube desde Spotify.**")
                        return
                    url = yt_link

            if is_playlist_url(url):
                songs = await fetch_playlist_songs(self.ytdl, url)
                if not songs:
                    await ctx.send("🚫 **La playlist de YouTube está vacía.**")
                    return

                if not is_playing:
                    # Reproducir la primera canción directamente
                    first_song_url, first_title, _ = songs[0]
                    songs_with_requester = [(song[0], song[1], ctx.author, song[2]) for song in songs[1:]]
                    self.queues[guild_id].extend(songs_with_requester)
                    await ctx.send(f"➕ **Añadida la playlist a la queue:** {len(songs)} canciones")
                    await self.play_song(ctx, first_song_url, first_title, ctx.author)
                else:
                    for song in reversed(songs):
                        self.queues[guild_id].insert(0, (song[0], song[1], ctx.author, song[2]))
                    await ctx.send(f"➕ **Añadida la playlist a la posición siguiente:** {len(songs)} canciones")
            else:
                if not is_youtube_url(url):
                    url = await search_youtube(url)
                    if not url:
                        await ctx.send("⚠️ **No se encontró ningún resultado en YouTube.**")
                        return

                video_info = await extract_video_info(self.ytdl, url)
                title = video_info['title']
                duration = video_info.get('duration', 0)

                if not is_playing:
                    await self.play_song(ctx, url, title, ctx.author)
                else:
                    self.queues[guild_id].insert(0, (url, title, ctx.author, duration))
                    await ctx.send(f"➕ ***{title}*** **ha sido añadida como la siguiente canción!**")

        except Exception as e:
            logging.error(f"Error en playnext: {e}")
            await ctx.send(f"⚠️ **Error al agregar la canción a la posición siguiente:** {e}")

    @commands.command(name="nowplaying", help="Muestra la canción que está sonando ahora mismo.")
    async def now_playing(self, ctx):
        guild_id = ctx.guild.id

        if (guild_id not in self.song_data or
            guild_id not in self.voice_clients or
            not (self.voice_clients[guild_id].is_playing() or
                 self.voice_clients[guild_id].is_paused())):
            await ctx.send("🚫 **No hay ninguna canción sonando ahora mismo!**")
            return

        # Deshabilitar controles anteriores si existen
        await self.disable_previous_controls(guild_id)

        embed = create_now_playing_embed(
            self.song_data, self.queues, self.loop_status,
            guild_id, ctx.author, autoplay_status=self.autoplay_status
        )

        view = MusicControls(
            ctx, None, self.voice_clients, self.loop_status,
            self.queues, self.song_data, self.manual_stop,
            bot=self.bot, autoplay_status=self.autoplay_status
        )

        message = await ctx.send(embed=embed, view=view)
        view.message = message
        view.update_button_states()
        await message.edit(view=view)

        # Guardar la vista activa
        self.active_controls_view[guild_id] = view
        view.start_update_loop()

    @commands.command(name="lyrics", help="Muestra las letras de la canción actual o de una búsqueda.")
    async def lyrics(self, ctx, *, query: str = None):
        guild_id = ctx.guild.id
        import os

        # Determinar qué canción buscar y obtener artista si está disponible
        song_artist = None
        if query:
            song_title = query
        elif guild_id in self.song_data:
            song_title = self.song_data[guild_id]['title']
            song_artist = self.song_data[guild_id].get('artist')
        else:
            await ctx.send("🚫 **No hay ninguna canción sonando y no especificaste qué buscar.**\n"
                          "Uso: `.lyrics` (canción actual) o `.lyrics <nombre de canción>`")
            return

        # Mensaje de búsqueda
        search_info = f"*{song_title}*"
        if song_artist:
            search_info = f"*{song_title}* de **{song_artist}**"
        search_msg = await ctx.send(f"🔍 **Buscando letras para:** {search_info}...")

        try:
            genius_api_key = os.getenv('GENIUS_API_KEY')
            lyrics_data = await get_lyrics(song_title, genius_api_key, song_artist)

            if not lyrics_data:
                await search_msg.edit(content=f"🚫 **No se encontraron letras para:** *{song_title}*")
                return

            # Obtener las letras (preferir plain sobre synced para el embed)
            lyrics_text = lyrics_data.get('plain') or lyrics_data.get('synced', '')

            # Limpiar letras sincronizadas si es necesario (remover timestamps)
            if lyrics_data.get('synced') and not lyrics_data.get('plain'):
                import re
                lyrics_text = re.sub(r'\[\d{2}:\d{2}\.\d{2}\]\s*', '', lyrics_text)

            max_length = 4000
            truncated = False
            if len(lyrics_text) > max_length:
                lyrics_text = lyrics_text[:max_length]
                last_newline = lyrics_text.rfind('\n')
                if last_newline > max_length - 500:
                    lyrics_text = lyrics_text[:last_newline]
                lyrics_text += "\n\n*[Letras truncadas...]*"
                truncated = True

            embed = discord.Embed(
                title=f"📝 {lyrics_data.get('title', song_title)}",
                description=lyrics_text,
                color=discord.Color.purple()
            )

            if lyrics_data.get('artist'):
                embed.set_author(name=lyrics_data['artist'])

            footer_text = f"Fuente: {lyrics_data.get('source', 'Desconocida')}"
            if lyrics_data.get('synced'):
                footer_text += " | Letras sincronizadas disponibles"
            embed.set_footer(text=footer_text)

            await search_msg.edit(content=None, embed=embed)

        except Exception as e:
            logging.error(f"Error obteniendo letras: {e}")
            await search_msg.edit(content=f"⚠️ **Error al buscar letras:** {e}")

    @commands.command(name="skip", help="Salta la canción actual.")
    async def skip(self, ctx):
        if not await self.ensure_voice(ctx):
            return

        guild_id = ctx.guild.id
        if await skip_song(guild_id, self.voice_clients):
            await ctx.send("⏭️ **Canción saltada!**")
        else:
            await ctx.send("🚫 **No hay ninguna canción reproduciéndose para saltar!**")

    @commands.command(name="skipto", help="Salta a una canción específica en la queue.")
    async def skip_to(self, ctx, posicion: int):
        guild_id = ctx.guild.id

        if guild_id not in self.queues or not (1 <= posicion <= len(self.queues[guild_id])):
            await ctx.send("🚫 **Posición inválida en la queue.**")
            return

        if guild_id in self.voice_clients and self.voice_clients[guild_id].is_playing():
            self.voice_clients[guild_id].stop()

        cancion = self.queues[guild_id].pop(posicion - 1)
        self.queues[guild_id].insert(0, cancion)

        await ctx.send(f"⏩ **Saltando a la canción número {posicion}:** *{cancion[1]}*!")

    @commands.command(name="clear", help="Limpia la queue actual.")
    async def clear_queue(self, ctx):
        if not await self.ensure_voice(ctx):
            return

        guild_id = ctx.guild.id
        if guild_id in self.queues:
            logging.info("Limpiando la queue.")
            self.queues[guild_id].clear()
            await ctx.send("🧹 **Se limpió la cola de canciones!**")
        else:
            await ctx.send("🚫 **No hay cola que limpiar!**")

    @commands.command(name="pause", help="Pausa la reproducción de la canción actual.")
    async def pause(self, ctx):
        if not await self.ensure_voice(ctx):
            return

        guild_id = ctx.guild.id
        if await pause_playback(guild_id, self.song_data, self.voice_clients):
            await ctx.send("⏸️ **Reproducción pausada!**")
        else:
            await ctx.send("🚫 **No hay nada reproduciéndose para pausar!**")

    @commands.command(name="resume", help="Reanuda la reproducción si está pausada.")
    async def resume(self, ctx):
        if not await self.ensure_voice(ctx):
            return

        guild_id = ctx.guild.id
        if await resume_playback(guild_id, self.song_data, self.voice_clients):
            await ctx.send("▶️ **Reproducción reanudada!**")
        else:
            await ctx.send("🚫 **No hay nada pausado para reanudar!**")

    @commands.command(name="loop", help="Activa o desactiva el loop de la canción actual.")
    async def loop_cmd(self, ctx):
        if not await self.ensure_voice(ctx):
            return

        guild_id = ctx.guild.id
        is_looping = toggle_loop(guild_id, self.loop_status)

        if is_looping:
            await ctx.send("🔁 **Loop activado!**")
        else:
            await ctx.send("🔁 **Loop desactivado!**")

    @commands.command(name="autoplay", aliases=["radio"], help="Activa o desactiva el autoplay de canciones relacionadas.")
    async def autoplay_cmd(self, ctx):
        if not await self.ensure_voice(ctx):
            return

        if not AUTOPLAY_ENABLED:
            await ctx.send("🚫 **El autoplay está deshabilitado en la configuración del bot.**")
            return

        guild_id = ctx.guild.id
        is_autoplay = toggle_autoplay(guild_id, self.autoplay_status)

        if is_autoplay:
            await ctx.send("📻 **Autoplay activado!** Cuando la queue termine, se reproducirán canciones parecidas.")
        else:
            await ctx.send("📻 **Autoplay desactivado!**")

    @commands.command(name="stop", help="Detiene la reproducción y limpia la queue.")
    async def stop(self, ctx):
        if not await self.ensure_voice(ctx):
            return

        guild_id = ctx.guild.id
        if guild_id in self.active_controls_view:
            self.active_controls_view[guild_id].cancel_update_loop()
        if await stop_playback(guild_id, self.voice_clients, self.queues, self.manual_stop, bot=self.bot):
            await ctx.send("⏹️ **Reproducción detenida!**")
        else:
            await ctx.send("🚫 **No hay ninguna canción sonando!**")

    @commands.command(name="shuffle", help="Mezcla aleatoriamente las canciones en la queue.")
    async def shuffle(self, ctx):
        guild_id = ctx.guild.id

        if await shuffle_queue(guild_id, self.queues):
            await ctx.send("🔀 **Queue mezclada!**")
        else:
            await ctx.send("🚫 **La queue está vacía!**")

    @commands.command(name="seek", help="Salta a un timestamp específico de la canción (ej: 1m30s, 90s, 2:15)")
    async def seek(self, ctx, *, timestamp: str):
        if not await self.ensure_voice(ctx):
            return

        guild_id = ctx.guild.id

        if guild_id not in self.voice_clients or not self.voice_clients[guild_id].is_connected():
            await ctx.send("🚫 **No estoy conectado a un canal de voz.**")
            return

        if not self.voice_clients[guild_id].is_playing() and not self.voice_clients[guild_id].is_paused():
            await ctx.send("🚫 **No hay ninguna canción reproduciéndose.**")
            return

        if guild_id not in self.song_data:
            await ctx.send("🚫 **No hay información de la canción actual.**")
            return

        seek_seconds = parse_time_string(timestamp)
        if seek_seconds is None:
            await ctx.send("⚠️ **Formato de tiempo inválido.** Usa formatos como: 1m30s, 90s, 2:15, 1:02:30")
            return

        song_duration = self.song_data[guild_id]['duration']
        if seek_seconds >= song_duration:
            formatted_duration = format_duration(song_duration)
            await ctx.send(f"⚠️ **El tiempo especificado ({format_duration(seek_seconds)}) excede la duración de la canción ({formatted_duration}).**")
            return

        try:
            current_url = self.song_data[guild_id]['url']
            current_title = self.song_data[guild_id]['title']

            self.seek_in_progress[guild_id] = True
            self.voice_clients[guild_id].stop()

            self.song_data[guild_id]['start_time'] = time.time() - seek_seconds
            self.song_data[guild_id]['paused_time'] = 0
            self.song_data[guild_id]['pause_start_time'] = 0

            video_info = await extract_video_info(self.ytdl, current_url)
            stream_url = video_info['stream_url']

            seek_ffmpeg_options = {
                'before_options': f'-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -ss {seek_seconds}',
                'options': f'-vn -filter:a "volume={PLAYBACK_VOLUME}"'
            }

            player = discord.FFmpegOpusAudio(stream_url, **seek_ffmpeg_options)
            self.voice_clients[guild_id].play(player, after=self.after_play(ctx))

            seek_time_str = format_duration(seek_seconds)
            await ctx.send(f"⏩ **Saltando a {seek_time_str} en:** *{current_title}*")

        except Exception as e:
            self.seek_in_progress[guild_id] = False
            logging.error(f"Error en seek: {e}")
            await ctx.send(f"⚠️ **Error al hacer seek:** {e}")

    @commands.command(name="move", help="Mueve una canción de una posición a otra en la queue.")
    async def move(self, ctx, desde: int, hasta: int):
        guild_id = ctx.guild.id

        if guild_id not in self.queues or not self.queues[guild_id]:
            await ctx.send("🚫 **La queue está vacía!**")
            return

        queue_len = len(self.queues[guild_id])
        if not (1 <= desde <= queue_len and 1 <= hasta <= queue_len):
            await ctx.send(f"🚫 **Las posiciones deben estar dentro del rango de la queue (1 a {queue_len}).**")
            return

        if desde == hasta:
            await ctx.send("ℹ️ **La canción ya está en esa posición.**")
            return

        song = self.queues[guild_id].pop(desde - 1)
        self.queues[guild_id].insert(hasta - 1, song)
        await ctx.send(f"🔀 **Movida** *{song[1]}* **de la posición {desde} a la {hasta}.**")

    @commands.command(name="remove", help="Remueve una canción de la queue por su posición.")
    async def remove(self, ctx, posicion: int):
        guild_id = ctx.guild.id

        if guild_id not in self.queues or not self.queues[guild_id]:
            await ctx.send("🚫 **La queue está vacía!**")
            return

        queue_len = len(self.queues[guild_id])
        if not (1 <= posicion <= queue_len):
            await ctx.send(f"🚫 **La posición debe estar dentro del rango de la queue (1 a {queue_len}).**")
            return

        song = self.queues[guild_id].pop(posicion - 1)
        await ctx.send(f"🗑️ **Removida** *{song[1]}* **de la posición {posicion}.**")

    @commands.command(name="leave", help="Desconecta el bot del canal de voz y borra la queue.")
    async def leave(self, ctx):
        guild_id = ctx.guild.id

        if guild_id in self.voice_clients:
            if guild_id in self.active_controls_view:
                self.active_controls_view[guild_id].cancel_update_loop()
            await self.voice_clients[guild_id].disconnect()
            del self.voice_clients[guild_id]
            if guild_id in self.queues:
                self.queues[guild_id].clear()
            await update_presence(self.bot, False)
            await ctx.send("👋 **Me he desconectado del canal de voz y la queue ha sido borrada.**")
        else:
            await ctx.send("🚫 **No estoy conectado a ningún canal de voz.**")

    @commands.command(name="search", help="Busca una canción y muestra 5 resultados para elegir.")
    async def search(self, ctx, *, query: str):
        if not await self.ensure_voice(ctx):
            return

        guild_id = ctx.guild.id
        if guild_id not in self.queues:
            self.queues[guild_id] = []

        search_msg = await ctx.send(f"🔍 **Buscando:** *{query}*...")

        try:
            urls = await search_youtube_multiple(query, max_results=SEARCH_MAX_RESULTS)

            if not urls:
                await search_msg.edit(content="⚠️ **No se encontraron resultados en YouTube.**")
                return

            # Obtener títulos y duraciones de los videos
            results = []
            for url in urls:
                try:
                    video_info = await extract_video_info(self.ytdl, url)
                    if video_info:
                        results.append((url, video_info['title'], video_info.get('duration', 0)))
                except Exception as e:
                    logging.debug(f"Error obteniendo info de {url}: {e}")
                    continue

            if not results:
                await search_msg.edit(content="⚠️ **No se pudieron obtener los resultados.**")
                return

            # Callback cuando se selecciona un resultado
            async def on_select(ctx, url, title, duration=0):
                is_playing = (guild_id in self.voice_clients and
                              (self.voice_clients[guild_id].is_playing() or
                               self.voice_clients[guild_id].is_paused()))

                if is_playing:
                    self.queues[guild_id].append((url, title, ctx.author, duration))
                    await ctx.send(f"➕ **Añadida a la queue:** *{title}*")
                else:
                    await self.play_song(ctx, url, title, ctx.author)

            embed = create_search_embed(query, results)
            view = SearchResultsView(ctx, results, on_select)

            await search_msg.edit(content=None, embed=embed, view=view)
            view.message = search_msg

        except Exception as e:
            logging.error(f"Error en búsqueda: {e}")
            await search_msg.edit(content=f"⚠️ **Error en la búsqueda:** {e}")

    # === STATS ===

    @commands.command(name="mystats", help="Muestra tus estadísticas de reproducciones en este servidor.")
    async def mystats(self, ctx):
        guild_id = ctx.guild.id
        user_id = ctx.author.id

        stats = get_user_stats(user_id, guild_id)

        if stats['total_listened'] == 0:
            await ctx.send("🚫 **No tienes reproducciones registradas en este servidor.**")
            return

        # Obtener top canciones del usuario
        top_songs = get_user_top_songs(user_id, guild_id, limit=USER_TOP_SONGS_LIMIT)

        embed = discord.Embed(
            title=f"📊 Estadísticas de {ctx.author.display_name}",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)

        embed.add_field(
            name="🎵 Canciones pedidas",
            value=str(stats['total_requested']),
            inline=True
        )
        embed.add_field(
            name="🎧 Canciones escuchadas",
            value=str(stats['total_listened']),
            inline=True
        )
        embed.add_field(
            name="⏱️ Tiempo total escuchado",
            value=format_duration(stats['total_time']),
            inline=True
        )

        if stats['first_play']:
            embed.add_field(
                name="📅 Primera reproducción",
                value=stats['first_play'][:10],
                inline=True
            )

        if top_songs:
            top_songs_text = "\n".join([
                f"**{i+1}.** {song[0]} ({song[2]} reproducciones)"
                for i, song in enumerate(top_songs)
            ])
            embed.add_field(
                name="🏆 Tus Top 5 canciones pedidas",
                value=top_songs_text,
                inline=False
            )

        embed.set_footer(text=f"Servidor: {ctx.guild.name}")
        await ctx.send(embed=embed)

    @commands.command(name="stats", help="Muestra las estadísticas de un usuario específico.")
    async def stats(self, ctx, member: discord.Member = None):
        if member is None:
            member = ctx.author

        guild_id = ctx.guild.id
        user_id = member.id

        stats = get_user_stats(user_id, guild_id)

        if stats['total_listened'] == 0:
            await ctx.send(f"🚫 **{member.display_name} no tiene reproducciones registradas en este servidor.**")
            return

        # Obtener top canciones del usuario
        top_songs = get_user_top_songs(user_id, guild_id, limit=USER_TOP_SONGS_LIMIT)

        embed = discord.Embed(
            title=f"📊 Estadísticas de {member.display_name}",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        embed.add_field(
            name="🎵 Canciones pedidas",
            value=str(stats['total_requested']),
            inline=True
        )
        embed.add_field(
            name="🎧 Canciones escuchadas",
            value=str(stats['total_listened']),
            inline=True
        )
        embed.add_field(
            name="⏱️ Tiempo total escuchado",
            value=format_duration(stats['total_time']),
            inline=True
        )

        if stats['first_play']:
            embed.add_field(
                name="📅 Primera reproducción",
                value=stats['first_play'][:10],
                inline=True
            )

        if top_songs:
            top_songs_text = "\n".join([
                f"**{i+1}.** {song[0]} ({song[2]} reproducciones)"
                for i, song in enumerate(top_songs)
            ])
            embed.add_field(
                name="🏆 Top 5 canciones pedidas",
                value=top_songs_text,
                inline=False
            )

        embed.set_footer(text=f"Servidor: {ctx.guild.name}")
        await ctx.send(embed=embed)

    @commands.command(name="topsongs", help="Muestra las canciones más reproducidas en este servidor.")
    async def topsongs(self, ctx):
        guild_id = ctx.guild.id

        top_songs = get_server_top_songs(guild_id, limit=TOP_SONGS_LIMIT)

        if not top_songs:
            await ctx.send("🚫 **No hay reproducciones registradas en este servidor.**")
            return

        embed = discord.Embed(
            title=f"🎵 Top {TOP_SONGS_LIMIT} Canciones - {ctx.guild.name}",
            color=discord.Color.purple()
        )

        songs_text = []
        for i, song in enumerate(top_songs):
            medal = ""
            if i == 0:
                medal = "🥇 "
            elif i == 1:
                medal = "🥈 "
            elif i == 2:
                medal = "🥉 "

            artist_text = f" - *{song[1]}*" if song[1] else ""
            songs_text.append(f"{medal}**{i+1}.** {song[0]}{artist_text} ({song[2]} reproducciones)")

        embed.description = "\n".join(songs_text)
        embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
        await ctx.send(embed=embed)

    @commands.command(name="topusers", help="Muestra los usuarios con más requests en este servidor.")
    async def topusers(self, ctx):
        guild_id = ctx.guild.id

        top_users = get_server_top_users(guild_id, limit=TOP_USERS_LIMIT)

        if not top_users:
            await ctx.send("🚫 **No hay reproducciones registradas en este servidor.**")
            return

        embed = discord.Embed(
            title=f"👑 Top {TOP_USERS_LIMIT} Usuarios - {ctx.guild.name}",
            color=discord.Color.orange()
        )

        users_text = []
        for i, user_data in enumerate(top_users):
            user_id, user_name, play_count, total_time = user_data
            medal = ""
            if i == 0:
                medal = "🥇 "
            elif i == 1:
                medal = "🥈 "
            elif i == 2:
                medal = "🥉 "

            time_str = format_duration(total_time)
            users_text.append(f"{medal}**{i+1}.** {user_name} - {play_count} requests ({time_str})")

        embed.description = "\n".join(users_text)
        embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
        await ctx.send(embed=embed)

    @commands.command(name="history", help="Muestra tu historial de reproducciones recientes.")
    async def history(self, ctx, member: discord.Member = None):
        if member is None:
            member = ctx.author

        guild_id = ctx.guild.id
        user_id = member.id

        history = get_user_history(user_id, guild_id, limit=HISTORY_LIMIT)

        if not history:
            if member == ctx.author:
                await ctx.send("🚫 **No tienes historial de reproducciones en este servidor.**")
            else:
                await ctx.send(f"🚫 **{member.display_name} no tiene historial de reproducciones en este servidor.**")
            return

        embed = discord.Embed(
            title=f"📜 Historial de {member.display_name}",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        history_text = []
        for i, (song_title, artist, played_at) in enumerate(history):
            # Formatear la fecha
            date_str = played_at[:16].replace("T", " ") if "T" in played_at else played_at[:16]
            song_info = f"**{i+1}.** {song_title}"
            if artist:
                song_info += f" - *{artist}*"
            song_info += f"\n   └ {date_str}"
            history_text.append(song_info)

        embed.description = "\n".join(history_text)
        embed.set_footer(text=f"Últimas {HISTORY_LIMIT} reproducciones en {ctx.guild.name}")
        await ctx.send(embed=embed)

    @commands.command(name="help", help="Muestra una lista de comandos disponibles.")
    async def show_commands(self, ctx):
        from views.help_menu import HelpMenuView

        view = HelpMenuView(ctx, self.bot)
        embed = view._create_summary_embed()

        message = await ctx.send(embed=embed, view=view)
        view.message = message


async def setup(bot):
    """Función de setup para cargar el Cog (requiere credenciales de Spotify)"""
    import os
    from dotenv import load_dotenv
    load_dotenv()

    spotify_client_id = os.getenv('SPOTIPY_CLIENT_ID')
    spotify_client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')

    await bot.add_cog(MusicCommands(bot, spotify_client_id, spotify_client_secret))
