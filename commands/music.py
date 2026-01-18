"""
Cog de comandos de música
"""
ALONE_TIMEOUT_SECONDS = 60  # Tiempo en segundos antes de desconectarse si el bot está solo

import discord
from discord.ext import commands
import asyncio
import time
import random
import logging

from core.formatters import format_duration, parse_time_string
from core.playback import (
    pause_playback,
    resume_playback,
    skip_song,
    toggle_loop,
    shuffle_queue,
    stop_playback
)
from core.youtube_handler import (
    create_ytdl,
    search_youtube,
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

        # Clientes externos
        self.ytdl = create_ytdl()
        self.sp = create_spotify_client(spotify_client_id, spotify_client_secret)

        # Opciones de FFmpeg
        self.ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn -filter:a "volume=0.375"'
        }

    async def disable_previous_controls(self, guild_id: int):
        """Deshabilita los controles del embed anterior si existe"""
        if guild_id in self.active_controls_view:
            old_view = self.active_controls_view[guild_id]
            try:
                for item in old_view.children:
                    item.disabled = True
                if old_view.message:
                    await old_view.message.edit(view=old_view)
            except Exception as e:
                logging.debug(f"No se pudo deshabilitar controles anteriores: {e}")
            del self.active_controls_view[guild_id]

    async def update_presence(self, listening: bool, song_title: str = ""):
        """Actualiza la presencia del bot"""
        if not listening:
            mensajes = [
                "Nada 🦗", 
                "Silencio total 🌃"
            ]
        else:
            mensajes = [
                f"{song_title}"
            ]

        mensaje = random.choice(mensajes)
        activity = discord.Activity(
            type=discord.ActivityType.listening,
            name=mensaje
        )
        await self.bot.change_presence(activity=activity)

    async def ensure_voice(self, ctx) -> bool:
        """Verifica que el usuario esté en un canal de voz y conecta el bot si es necesario"""
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("🚫 **Debes estar en un canal de voz para usar este comando.**")
            return False

        guild_id = ctx.guild.id
        if guild_id not in self.voice_clients or not self.voice_clients[guild_id].is_connected():
            try:
                logging.info(f"Intentando conectarse al canal de voz: {ctx.author.voice.channel}")
                voice_client = await ctx.author.voice.channel.connect(timeout=60.0)
                self.voice_clients[guild_id] = voice_client
                logging.info(f"Conectado a: {ctx.author.voice.channel}")
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

    async def play_song(self, ctx, url: str, title: str = None):
        """Reproduce una canción"""
        try:
            logging.info(f"Attempting to play song: {url}")
            video_info = await extract_video_info(self.ytdl, url)

            if not video_info:
                raise Exception("No se pudo obtener el URL del stream")

            stream_url = video_info['stream_url']
            actual_title = title if title else video_info['title']

            logging.info(f"Stream URL obtained: {stream_url[:100]}...")
            logging.info(f"Format ID: {video_info['format_id']}")

            guild_id = ctx.guild.id

            # Resetear la bandera manual_stop
            self.manual_stop[guild_id] = False

            # Guardar información de la canción actual
            self.current_song[guild_id] = actual_title
            self.current_song_url[guild_id] = url

            self.song_data[guild_id] = {
                'title': actual_title,
                'url': url,
                'duration': video_info['duration'],
                'start_time': time.time(),
                'paused_time': 0,
                'pause_start_time': 0
            }

            await self.update_presence(True, actual_title)

            logging.info("Creating FFmpegOpusAudio player...")
            player = discord.FFmpegOpusAudio(stream_url, **self.ffmpeg_options)

            logging.info("Starting playback on voice client...")
            self.voice_clients[guild_id].play(player, after=self.after_play(ctx))

            await asyncio.sleep(0.5)

            if self.voice_clients[guild_id].is_playing():
                logging.info(f"Confirmed: Audio is playing for: {actual_title}")
            else:
                logging.error(f"Audio is NOT playing after start command for: {actual_title}")

            # Deshabilitar controles anteriores si existen
            await self.disable_previous_controls(guild_id)

            # Crear embed y vista con controles
            embed = create_now_playing_embed(
                self.song_data, self.queues, self.loop_status,
                guild_id, ctx.author
            )

            view = MusicControls(
                ctx, None, self.voice_clients, self.loop_status,
                self.queues, self.song_data, self.manual_stop
            )

            message = await ctx.send(embed=embed, view=view)
            view.message = message
            view.update_button_states()
            await message.edit(view=view)

            # Guardar la vista activa
            self.active_controls_view[guild_id] = view

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
            if last_link:
                logging.info(f"Looping song: {last_title}")
                await self.play_song(ctx, last_link, last_title)
                return

        if url:
            logging.info(f"Playing next song: {url}")
            await self.play_song(ctx, url)
        elif self.queues.get(guild_id):
            next_link, next_title = self.queues[guild_id].pop(0)
            logging.info(f"Playing next song from queue: {next_title}")
            await self.play_song(ctx, next_link, next_title)
        else:
            logging.info("La queue está vacía, no hay nada que reproducir.")
            await self.update_presence(False)
            await ctx.send("🚫 **La queue está vacía.**")

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
                    self.voice_clients[guild_id].stop()
                    if guild_id in self.queues:
                        self.queues[guild_id].clear()

                    await self.voice_clients[guild_id].disconnect()
                    del self.voice_clients[guild_id]

                    await self.update_presence(False)

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
        await self.update_presence(False)
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
                    first_song_url, first_title = songs[0]
                    self.queues[guild_id].extend(songs[1:])
                    await self.play_song(ctx, first_song_url, first_title)
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
                first_song_url, first_title = songs[0]
                self.queues[guild_id].extend(songs[1:])
                await ctx.send(f"➕ **Añadida la playlist a la queue:** {len(songs)} canciones")
                await self.play_song(ctx, first_song_url, first_title)
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
                    self.queues[guild_id].extend(songs)
                    await ctx.send(f"➕ **Añadida la playlist a la queue:** {len(songs)} canciones")
                    return
                else:
                    track_id = extract_track_id_from_url(url)
                    yt_link, title = await get_youtube_url_from_spotify_track(self.sp, url)
                    if not yt_link:
                        await ctx.send("⚠️ **Error al obtener el enlace de YouTube desde Spotify.**")
                        return
                    self.queues[guild_id].append((yt_link, title))
                    await ctx.send(f"➕ **Añadida a la queue:** *{title}*")
                    return

            if is_playlist_url(url):
                songs = await fetch_playlist_songs(self.ytdl, url)
                if not songs:
                    await ctx.send("🚫 **La playlist de YouTube está vacía.**")
                    return
                self.queues[guild_id].extend(songs)
                await ctx.send(f"➕ **Añadida la playlist a la queue:** {len(songs)} canciones")
            else:
                if not is_youtube_url(url):
                    url = await search_youtube(url)
                    if not url:
                        await ctx.send("⚠️ **No se encontró ningún resultado en YouTube.**")
                        return

                video_info = await extract_video_info(self.ytdl, url)
                title = video_info['title']
                self.queues[guild_id].append((url, title))
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

        items_per_page = 25
        total_songs = len(self.queues[guild_id])
        pages = [self.queues[guild_id][i:i + items_per_page]
                 for i in range(0, len(self.queues[guild_id]), items_per_page)]

        paginator = QueuePaginator(ctx, pages, total_songs, items_per_page)
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

        try:
            if is_spotify_url(url):
                if is_spotify_playlist(url):
                    songs = await fetch_spotify_playlist_tracks(self.sp, url)
                    if not songs:
                        await ctx.send("🚫 **La playlist de Spotify está vacía.**")
                        return
                    for song in reversed(songs):
                        self.queues[guild_id].insert(0, song)
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
                for song in reversed(songs):
                    self.queues[guild_id].insert(0, song)
                await ctx.send(f"➕ **Añadida la playlist a la posición siguiente:** {len(songs)} canciones")
            else:
                if not is_youtube_url(url):
                    url = await search_youtube(url)
                    if not url:
                        await ctx.send("⚠️ **No se encontró ningún resultado en YouTube.**")
                        return

                video_info = await extract_video_info(self.ytdl, url)
                title = video_info['title']
                self.queues[guild_id].insert(0, (url, title))
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
            guild_id, ctx.author
        )

        view = MusicControls(
            ctx, None, self.voice_clients, self.loop_status,
            self.queues, self.song_data, self.manual_stop
        )

        message = await ctx.send(embed=embed, view=view)
        view.message = message
        view.update_button_states()
        await message.edit(view=view)

        # Guardar la vista activa
        self.active_controls_view[guild_id] = view

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

    @commands.command(name="stop", help="Detiene la reproducción y limpia la queue.")
    async def stop(self, ctx):
        if not await self.ensure_voice(ctx):
            return

        guild_id = ctx.guild.id
        if await stop_playback(guild_id, self.voice_clients, self.queues, self.manual_stop):
            await self.update_presence(False)
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
                'options': '-vn -filter:a "volume=0.375"'
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

    @commands.command(name="leave", help="Desconecta el bot del canal de voz y borra la queue.")
    async def leave(self, ctx):
        guild_id = ctx.guild.id

        if guild_id in self.voice_clients:
            await self.voice_clients[guild_id].disconnect()
            del self.voice_clients[guild_id]
            if guild_id in self.queues:
                self.queues[guild_id].clear()
            await self.update_presence(False)
            await ctx.send("👋 **Me he desconectado del canal de voz y la queue ha sido borrada.**")
        else:
            await ctx.send("🚫 **No estoy conectado a ningún canal de voz.**")

    @commands.command(name="help", help="Muestra una lista de comandos disponibles.")
    async def show_commands(self, ctx):
        embed = discord.Embed(title="📋 Comandos disponibles", color=discord.Color.blue())

        for command in sorted(self.bot.commands, key=lambda c: c.name):
            # Construir el nombre con parámetros
            params = []
            for param_name, param in command.clean_params.items():
                if param.default == param.empty:
                    params.append(f"<{param_name}>")
                else:
                    params.append(f"[{param_name}]")

            cmd_signature = f".{command.name}"
            if params:
                cmd_signature += " " + " ".join(params)

            # Usar la descripción del comando o un texto por defecto
            description = command.help or "Sin descripción"

            embed.add_field(name=cmd_signature, value=description, inline=False)

        embed.set_footer(text=f"Total: {len(self.bot.commands)} comandos")
        await ctx.send(embed=embed)


async def setup(bot):
    """Función de setup para cargar el Cog (requiere credenciales de Spotify)"""
    import os
    from dotenv import load_dotenv
    load_dotenv()

    spotify_client_id = os.getenv('SPOTIPY_CLIENT_ID')
    spotify_client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')

    await bot.add_cog(MusicCommands(bot, spotify_client_id, spotify_client_secret))
