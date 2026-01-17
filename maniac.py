import discord
from discord.ext import commands
import os
import asyncio
import yt_dlp
from dotenv import load_dotenv
import urllib.parse, re
import logging
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import aiohttp
from collections import defaultdict
import random
import time
import tkinter as tk
from tkinter import scrolledtext
import threading
import pystray
from PIL import Image, ImageDraw
import sys
from io import StringIO

# Configurar logging personalizado
logging.getLogger('discord').setLevel(logging.WARNING)

# Handler personalizado para capturar logs y mostrarlos en la GUI
class TextHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        # Determinar el tag según el nivel de log
        level = record.levelname
        if level == 'ERROR' or level == 'CRITICAL':
            tag = 'error'
        elif level == 'WARNING':
            tag = 'warning'
        elif level == 'INFO':
            tag = 'info'
        elif level == 'DEBUG':
            tag = 'debug'
        else:
            tag = 'default'

        def append():
            if self.text_widget and self.text_widget.winfo_exists():
                self.text_widget.configure(state='normal')
                self.text_widget.insert(tk.END, msg + '\n', tag)
                self.text_widget.configure(state='disabled')
                self.text_widget.yview(tk.END)
        if self.text_widget:
            self.text_widget.after(0, append)

# Clase para redirigir stdout/stderr al text widget
class StreamRedirector:
    def __init__(self, text_widget, stream_type='stdout'):
        self.text_widget = text_widget
        self.stream_type = stream_type
        self.buffer = ""

    def write(self, text):
        def append():
            if self.text_widget and self.text_widget.winfo_exists():
                self.text_widget.configure(state='normal')
                self.text_widget.insert(tk.END, text)
                self.text_widget.configure(state='disabled')
                self.text_widget.yview(tk.END)

        if self.text_widget and text.strip():  # Solo si hay texto
            self.text_widget.after(0, append)

    def flush(self):
        pass  # Necesario para compatibilidad con sys.stdout/stderr

youtube_url_cache = defaultdict(str)

# Clase para la ventana de logs
class LogWindow:
    def __init__(self):
        self.window = None
        self.text_area = None
        self.icon = None
        self.is_visible = False
        self.pending_action = None

    def create_image(self):
        # Crear un icono simple para el system tray
        width = 64
        height = 64
        color1 = (0, 120, 212)  # Azul
        color2 = (255, 255, 255)  # Blanco

        image = Image.new('RGB', (width, height), color1)
        dc = ImageDraw.Draw(image)

        # Dibujar una nota musical simple
        dc.ellipse([20, 35, 35, 50], fill=color2)
        dc.rectangle([32, 15, 38, 42], fill=color2)

        return image

    def setup_window(self):
        """Configurar la ventana inicial"""
        self.window = tk.Tk()
        self.window.title("Music Maniac - Bot Logs")
        self.window.geometry("800x600")

        # Configurar el cierre de la ventana
        self.window.protocol("WM_DELETE_WINDOW", self.hide_window)

        # Crear área de texto con scroll
        self.text_area = scrolledtext.ScrolledText(
            self.window,
            state='disabled',
            bg='#1e1e1e',
            fg='#d4d4d4',
            font=('Consolas', 10),
            wrap=tk.WORD
        )
        self.text_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Configurar tags para colores según el nivel de log
        self.text_area.tag_config('error', foreground='#f44747')      # Rojo para errores
        self.text_area.tag_config('warning', foreground='#ff8c00')    # Naranja para warnings
        self.text_area.tag_config('info', foreground='#4fc3f7')       # Azul claro para info
        self.text_area.tag_config('debug', foreground='#a9a9a9')      # Gris para debug
        self.text_area.tag_config('default', foreground='#d4d4d4')    # Blanco/gris claro por defecto

        # Configurar logging para capturar TODO
        text_handler = TextHandler(self.text_area)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        text_handler.setFormatter(formatter)

        # Configurar el logger raíz para capturar todos los logs
        root_logger = logging.getLogger()
        root_logger.addHandler(text_handler)
        root_logger.setLevel(logging.DEBUG)

        # Asegurarse de que yt-dlp también loggee
        logging.getLogger('yt_dlp').setLevel(logging.DEBUG)
        logging.getLogger('yt_dlp').addHandler(text_handler)

        # Mensaje de bienvenida
        self.text_area.configure(state='normal')
        self.text_area.insert(tk.END, "=== Music Maniac Bot Log Window ===\n")
        self.text_area.insert(tk.END, "Bot iniciado correctamente.\n\n")
        self.text_area.configure(state='disabled')

        # Inicialmente oculta
        self.window.withdraw()

    def toggle_window(self, icon=None, item=None):
        if self.is_visible:
            self.pending_action = 'hide'
        else:
            self.pending_action = 'show'

    def show_window(self):
        if self.window:
            self.window.deiconify()
            self.window.lift()
            self.window.focus_force()
            self.is_visible = True

    def hide_window(self):
        if self.window:
            self.window.withdraw()
            self.is_visible = False

    def check_pending_actions(self):
        """Revisar si hay acciones pendientes y ejecutarlas"""
        if self.pending_action == 'show':
            self.show_window()
            self.pending_action = None
        elif self.pending_action == 'hide':
            self.hide_window()
            self.pending_action = None

        # Volver a revisar en 100ms
        if self.window:
            self.window.after(100, self.check_pending_actions)

    def setup_tray_icon(self):
        image = self.create_image()
        menu = pystray.Menu(
            pystray.MenuItem("Mostrar/Ocultar Logs", self.toggle_window, default=True),
            pystray.MenuItem("Salir", self.quit_app)
        )
        self.icon = pystray.Icon("MusicManiac", image, "Music Maniac Bot", menu)

    def quit_app(self, icon=None, item=None):
        if self.icon:
            self.icon.stop()
        if self.window:
            self.window.quit()
        os._exit(0)

    def run_tray(self):
        # El tray icon corre en un thread separado
        self.setup_tray_icon()
        self.icon.run()

    def run(self):
        """Ejecutar la aplicación en el thread principal"""
        self.setup_window()
        self.check_pending_actions()
        self.window.mainloop()

# Variable global para la ventana de logs
log_window = LogWindow()

# Clase para manejar la paginación de la queue
class QueuePaginator(discord.ui.View):
    def __init__(self, ctx, pages, total_songs):
        super().__init__(timeout=180) # Timeout de 3 minutos
        self.ctx = ctx
        self.pages = pages
        self.total_songs = total_songs
        self.current_page = 0
        self.total_pages = len(pages)
        self.items_per_page = 10

    def create_embed(self):
        page_content = self.pages[self.current_page]
        start_index = self.current_page * self.items_per_page
        queue_list = [f"**{i + 1 + start_index}.** *{title}*" for i, (url, title) in enumerate(page_content)]
        description = "\n".join(queue_list)
        
        embed = discord.Embed(
            title=f"Queue Actual (Página {self.current_page + 1}/{self.total_pages})",
            description=description,
            color=discord.Color.blurple()
        )
        embed.set_footer(text=f"Total de canciones: {self.total_songs}")

        return embed

    async def update_message(self, interaction: discord.Interaction):
        # Habilitar/deshabilitar botones según la página actual
        self.children[0].disabled = self.current_page == 0
        self.children[1].disabled = self.current_page >= self.total_pages - 1
        
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="⬅️ Anterior", style=discord.ButtonStyle.secondary, custom_id="prev_page")
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("🚫 ¡No puedes usar estos botones!", ephemeral=True)
            return
            
        if self.current_page > 0:
            self.current_page -= 1
            await self.update_message(interaction)

    @discord.ui.button(label="Siguiente ➡️", style=discord.ButtonStyle.secondary, custom_id="next_page")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("🚫 ¡No puedes usar estos botones!", ephemeral=True)
            return

        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            await self.update_message(interaction)

async def run_bot():
    load_dotenv()
    TOKEN = os.getenv('discord_token')
    SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
    SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
    
    intents = discord.Intents.default()
    intents.message_content = True
    client = commands.Bot(command_prefix=".", intents=intents, case_insensitive=True)

    queues = {}
    voice_clients = {}
    loop_status = {}
    current_song = {}
    current_song_url = {}
    skipto_in_progress = {}
    manual_stop = {}
    seek_in_progress = {}
    alone_timeout_tasks = {}  # Tareas de timeout cuando el bot está solo
    last_text_channel = {}  # Último canal de texto usado por servidor

    song_data = {} # Guardará todo: { guild_id: { 'title': '...', 'url': '...', 'duration': 300, 'start_time': 167... } }

    youtube_base_url = 'https://www.youtube.com/'
    youtube_results_url = 'https://www.youtube.com/results?'

    # Crear un logger para yt-dlp
    class YTDLLogger:
        def debug(self, msg):
            if msg.startswith('[debug] '):
                pass  # Ignorar mensajes de debug muy verbosos
            else:
                logging.debug(msg)

        def info(self, msg):
            logging.info(msg)

        def warning(self, msg):
            logging.warning(msg)

        def error(self, msg):
            logging.error(msg)

    yt_dl_options = {
        "format": "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best",
        "noplaylist": True,
        "extract_flat": "in_playlist",
        "extractor_args": {
            "youtube": {
                "player_client": ["ios", "android", "web"]
            }
        },
        "nocheckcertificate": True,
        "logger": YTDLLogger(),
        "progress_hooks": [],
        "geo_bypass": True,
        "age_limit": None,
    }
    ytdl = yt_dlp.YoutubeDL(yt_dl_options)

    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn -filter:a "volume=0.375"'  # 1.5 * 0.25 = 0.375 para mantener el mismo volumen
    }

    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET
    ))

    @client.event
    async def on_ready():
        print(f'{client.user} is now jamming')
        await update_presence(False, "Nada sonando")

    @client.event
    async def on_command(ctx):
        """Guardar el último canal de texto usado para cada servidor"""
        last_text_channel[ctx.guild.id] = ctx.channel

    @client.event
    async def on_voice_state_update(member, before, after):
        """Detecta cuando el bot se queda solo en el canal de voz"""
        try:
            guild_id = member.guild.id

            # Verificar si el bot está conectado a un canal de voz en este servidor
            if guild_id not in voice_clients or not voice_clients[guild_id].is_connected():
                return

            voice_channel = voice_clients[guild_id].channel

            # Contar cuántos miembros NO son bots están en el canal
            human_members = [m for m in voice_channel.members if not m.bot]

            # Si el bot está solo (sin humanos)
            if len(human_members) == 0:
                # Si no hay una tarea de timeout activa, crearla
                if guild_id not in alone_timeout_tasks or alone_timeout_tasks[guild_id].done():
                    logging.info(f"Bot quedó solo en guild {guild_id}, iniciando timeout de 5 minutos")

                    # Usar el último canal de texto guardado, o el primero disponible
                    text_channel = last_text_channel.get(guild_id)
                    if not text_channel or not text_channel in member.guild.text_channels:
                        text_channel = member.guild.text_channels[0] if member.guild.text_channels else None

                    if text_channel:
                        # Crear y guardar la tarea de timeout
                        task = asyncio.create_task(alone_timeout(guild_id, text_channel))
                        alone_timeout_tasks[guild_id] = task
                    else:
                        logging.warning(f"No se encontró canal de texto para enviar mensaje en guild {guild_id}")
            else:
                # Hay al menos un humano en el canal, cancelar timeout si existe
                if guild_id in alone_timeout_tasks and not alone_timeout_tasks[guild_id].done():
                    logging.info(f"Alguien se unió al canal en guild {guild_id}, cancelando timeout")
                    alone_timeout_tasks[guild_id].cancel()
                    del alone_timeout_tasks[guild_id]

        except Exception as e:
            logging.error(f"Error en on_voice_state_update: {e}")

    async def update_presence(listening, song_title):
        if not listening:
            mensajes = ["nada 🦗", "silencio total 🌃"]
        else:
            mensajes = [
                f"banger: {song_title} 🔥",
                f"🎵 {song_title}",
                f"a todo volumen {song_title} 🔊"
            ]
        
        mensaje = random.choice(mensajes)
        
        activity = discord.Activity(
            type=discord.ActivityType.listening, 
            name=mensaje
        )
        
        await client.change_presence(activity=activity)

    async def play_song(ctx, link, title=None):
        try:
            logging.info(f"Attempting to play song: {link}")
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(link, download=False))

            if 'url' not in data:
                logging.error(f"No URL found in data. Available keys: {list(data.keys())}")
                raise Exception("No se pudo obtener el URL del stream")

            stream_url = data['url']
            actual_title = title if title else data.get('title', 'Unknown Title')

            logging.info(f"Stream URL obtained: {stream_url[:100]}...")  # Log primeros 100 chars
            logging.info(f"Format ID: {data.get('format_id', 'unknown')}")
            logging.info(f"Extension: {data.get('ext', 'unknown')}")

            guild_id = ctx.guild.id

            # Resetear la bandera manual_stop al iniciar una nueva reproducción
            manual_stop[guild_id] = False

            # Guardar la información de la canción actual para el loop
            current_song[guild_id] = actual_title
            current_song_url[guild_id] = link

            song_data[guild_id] = {
                'title': actual_title,
                'url': link,
                'duration': data.get('duration', 0), # Duración en segundos
                'start_time': time.time(), # Momento exacto en que empieza
                'paused_time': 0, # Tiempo total que ha estado en pausa
                'pause_start_time': 0 # Para calcular la duración de la pausa actual
            }

            await update_presence(True, actual_title)

            logging.info(f"Creating FFmpegOpusAudio player...")
            
            # Usar FFmpegOpusAudio para mejor calidad (codificación directa sin recodificación)
            player = discord.FFmpegOpusAudio(stream_url, **ffmpeg_options)

            logging.info(f"Starting playback on voice client...")
            voice_clients[ctx.guild.id].play(player, after=after_play(ctx))

            await asyncio.sleep(0.5)

            if voice_clients[ctx.guild.id].is_playing():
                logging.info(f"✓ Confirmed: Audio is playing for: {actual_title}")
            else:
                logging.error(f"✗ Audio is NOT playing after start command for: {actual_title}")

            message = f"🎵 **Sonando ahora:** [{actual_title}]({link})"
            if ctx.author.id == 541919270724960256:
                message += " 🥱"

            await ctx.send(message)
        except Exception as e:
            logging.error(f"Error playing song: {e}")
            logging.error(f"Exception traceback:", exc_info=True)
            await ctx.send(f"⚠️ **Error al reproducir la canción: {e}. Saltando a la siguiente...**")
            await play_next(ctx)

    async def play_next(ctx, link=None):
        if ctx.guild.id in skipto_in_progress and skipto_in_progress[ctx.guild.id]:
            skipto_in_progress[ctx.guild.id] = False
            return
        if ctx.guild.id in seek_in_progress and seek_in_progress[ctx.guild.id]:
            seek_in_progress[ctx.guild.id] = False
            return
        if loop_status.get(ctx.guild.id, False):
            last_link = current_song_url.get(ctx.guild.id)
            last_title = current_song.get(ctx.guild.id)
            if last_link:
                logging.info(f"Looping song: {last_title}")
                await play_song(ctx, last_link, last_title)
                return
        elif link:
            logging.info(f"Playing next song: {link}")
            await play_song(ctx, link)
        elif queues.get(ctx.guild.id):
            next_link, next_title = queues[ctx.guild.id].pop(0)
            logging.info(f"Playing next song from queue: {next_title}")
            await play_song(ctx, next_link, next_title)
        else:
            logging.info("La queue está vacía, no hay nada que reproducir.")
            await update_presence(False, "Nada sonando")
            await ctx.send("🚫 **La queue está vacía.**")

    def after_play(ctx):
        def _after_play(error):
            if error:
                logging.error(f"Error in after_play callback: {error}")
                logging.error(f"Error type: {type(error)}")
            else:
                logging.info(f"Song finished playing normally in guild {ctx.guild.id}")

            if ctx.guild.id not in voice_clients or not voice_clients[ctx.guild.id].is_connected():
                logging.warning(f"Voice client not connected for guild {ctx.guild.id}")
                return
            if manual_stop.get(ctx.guild.id, False):
                logging.info(f"Manual stop detected for guild {ctx.guild.id}")
                manual_stop[ctx.guild.id] = False
                return

            logging.info(f"Calling play_next for guild {ctx.guild.id}")
            coro = play_next(ctx)
            fut = asyncio.run_coroutine_threadsafe(coro, client.loop)
            try:
                fut.result()
            except Exception as e:
                logging.error(f"Error running play_next: {e}")
        return _after_play

    async def fetch_playlist_songs(url):
        data = ytdl.extract_info(url, download=False)
        songs = [(youtube_base_url + 'watch?v=' + entry['id'], entry['title']) for entry in data['entries']]
        return songs

    async def get_youtube_url_from_spotify(spotify_url):
        try:
            track_info = sp.track(spotify_url)
            track_name = track_info['name']
            artist_name = track_info['artists'][0]['name']
            search_query = f"{track_name} {artist_name}"
            query_string = urllib.parse.urlencode({'search_query': search_query})
            async with aiohttp.ClientSession() as session:
                async with session.get(youtube_results_url + query_string) as response:
                    content = await response.text()
                    search_results = re.findall(r'/watch\?v=(.{11})', content)
                    if not search_results:
                        logging.error("No se encontraron resultados en YouTube para la búsqueda.")
                        return None
                    return youtube_base_url + 'watch?v=' + search_results[0]
        except Exception as e:
            logging.error(f"Error fetching YouTube URL from Spotify: {e}")
            return None

    async def get_youtube_url_from_spotify_track(track_id, session):
        try:
            track = sp.track(track_id)
            track_name = track['name']
            artist_name = track['artists'][0]['name']
            search_query = f"{track_name} {artist_name}"
            query_string = urllib.parse.urlencode({'search_query': search_query})
            async with session.get(youtube_results_url + query_string) as response:
                content = await response.text()
                search_results = re.findall(r'/watch\?v=(.{11})', content)
                if not search_results:
                    logging.error("No se encontraron resultados en YouTube para el track de Spotify.")
                    return None, None
                youtube_url = youtube_base_url + 'watch?v=' + search_results[0]
                youtube_url_cache[track['id']] = youtube_url
                return youtube_url, track_name
        except Exception as e:
            logging.error(f"Error fetching YouTube URL from Spotify track: {e}")
            return None, None

    async def fetch_spotify_playlist_tracks(spotify_url):
        try:
            playlist_id = spotify_url.split("/")[-1].split("?")[0]
            results = sp.playlist_tracks(playlist_id)
            tracks = results['items']
            songs = []
            async with aiohttp.ClientSession() as session:
                tasks = []
                for item in tracks:
                    track = item['track']
                    if not track: continue
                    if track['id'] in youtube_url_cache:
                        youtube_url = youtube_url_cache[track['id']]
                        track_name = track['name']
                        songs.append((youtube_url, track_name))
                    else:
                        tasks.append(get_youtube_url_from_spotify_track(track['id'], session))
                results = await asyncio.gather(*tasks)
                songs.extend([result for result in results if result[0]])
            return songs
        except Exception as e:
            logging.error(f"Error fetching Spotify playlist tracks: {e}")
            return []

    async def ensure_voice(ctx):
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("🚫 **Debes estar en un canal de voz para usar este comando.**")
            return False
        if ctx.guild.id not in voice_clients or not voice_clients[ctx.guild.id].is_connected():
            try:
                logging.info(f"Intentando conectarse al canal de voz: {ctx.author.voice.channel}")
                voice_client = await ctx.author.voice.channel.connect(timeout=60.0)
                voice_clients[ctx.guild.id] = voice_client
                logging.info(f"Conectado a: {ctx.author.voice.channel}")
            except Exception as e:
                logging.error(f"Error al conectar al canal de voz: {e}")
                await ctx.send(f"⚠️ **Error al conectar al canal de voz: {e}**")
                return False
        return True

    async def alone_timeout(guild_id, channel):
        """Espera 5 minutos y desconecta el bot si sigue solo"""
        try:
            await asyncio.sleep(300)  # 5 minutos = 300 segundos

            # Verificar si el bot todavía está conectado y solo en el canal
            if guild_id in voice_clients and voice_clients[guild_id].is_connected():
                # Obtener el canal de voz actual del bot
                voice_channel = voice_clients[guild_id].channel

                # Contar cuántos miembros NO son bots están en el canal
                human_members = [member for member in voice_channel.members if not member.bot]

                if len(human_members) == 0:
                    # El bot sigue solo, desconectar
                    logging.info(f"Bot estuvo solo por 5 minutos en {guild_id}, desconectando...")

                    # Enviar mensaje en el último canal de texto usado
                    try:
                        await channel.send("Me quedé solo. Ya me voy 😔")
                    except Exception as e:
                        logging.error(f"Error al enviar mensaje de despedida: {e}")

                    # Detener reproducción y limpiar
                    manual_stop[guild_id] = True
                    voice_clients[guild_id].stop()
                    if guild_id in queues:
                        queues[guild_id].clear()

                    # Desconectar
                    await voice_clients[guild_id].disconnect()
                    del voice_clients[guild_id]

                    # Actualizar presencia
                    await update_presence(False, "Nada sonando")

                    # Limpiar la tarea
                    if guild_id in alone_timeout_tasks:
                        del alone_timeout_tasks[guild_id]
        except asyncio.CancelledError:
            logging.info(f"Timeout cancelado para guild {guild_id} - alguien se unió al canal")
        except Exception as e:
            logging.error(f"Error en alone_timeout: {e}")

    @client.command(name="play", help="Reproduce una canción o playlist desde YouTube o Spotify.")
    async def play(ctx, *, link):
        if not await ensure_voice(ctx): return
        if ctx.guild.id not in queues: queues[ctx.guild.id] = []

        if voice_clients[ctx.guild.id].is_playing() or voice_clients[ctx.guild.id].is_paused():
            await queue(ctx, url=link)
            return

        try:
            if "spotify.com" in link:
                if "playlist" in link:
                    await ctx.send("🔍 **Procesando playlist de Spotify... Esto puede tardar un momento.**")
                    songs = await fetch_spotify_playlist_tracks(link)
                    if not songs:
                        await ctx.send("🚫 **La playlist de Spotify está vacía o no se pudo procesar.**")
                        return
                    first_song_url, first_title = songs[0]
                    queues[ctx.guild.id].extend(songs[1:])
                    await play_song(ctx, first_song_url, first_title)
                    await ctx.send(f"➕ **Añadida la playlist a la queue:** {len(songs)} canciones")
                    return

                elif "track" in link:
                    yt_link = await get_youtube_url_from_spotify(link)
                    if not yt_link:
                        await ctx.send("⚠️ **Error al obtener el enlace de YouTube desde Spotify.**")
                        return
                    link = yt_link
                # ... resto de la lógica de spotify ...

            # Check if it's a playlist URL (not just a video with playlist parameters)
            if "playlist?list=" in link or ("list=" in link and "watch?v=" not in link):
                songs = await fetch_playlist_songs(link)
                if not songs:
                    await ctx.send("🚫 **La playlist de YouTube está vacía.**")
                    return
                first_song_url, first_title = songs[0]
                queues[ctx.guild.id].extend(songs[1:])
                await ctx.send(f"➕ **Añadida la playlist a la queue:** {len(songs)} canciones")
                await play_song(ctx, first_song_url, first_title)
            else:
                # Check if it's a valid YouTube URL (supporting various formats)
                if not any(domain in link.lower() for domain in ['youtube.com', 'youtu.be', 'm.youtube.com']):
                    query_string = urllib.parse.urlencode({'search_query': link})
                    async with aiohttp.ClientSession() as session:
                        async with session.get(youtube_results_url + query_string) as response:
                            content = await response.text()
                            search_results = re.findall(r'/watch\?v=(.{11})', content)
                            if not search_results:
                                await ctx.send("⚠️ **No se encontró ningún resultado en YouTube.**")
                                return
                            link = youtube_base_url + 'watch?v=' + search_results[0]
                else:
                    # Clean up URL - remove playlist parameters for individual video playback
                    if "watch?v=" in link and "&list=" in link:
                        # Extract just the video ID and create clean URL
                        video_match = re.search(r'watch\?v=([^&]+)', link)
                        if video_match:
                            video_id = video_match.group(1)
                            link = f"https://www.youtube.com/watch?v={video_id}"
                await play_song(ctx, link)
        except Exception as e:
            logging.error(f"Error al reproducir la canción: {e}")
            await ctx.send(f"⚠️ **Error al reproducir la canción: {e}**")

    @client.command(name="add", help="Añade una canción o playlist a la queue.")
    async def queue(ctx, *, url):
        if not await ensure_voice(ctx): return
        if ctx.guild.id not in queues: queues[ctx.guild.id] = []
        try:
            if "spotify.com" in url:
                if "playlist" in url:
                    await ctx.send("🔍 **Procesando playlist de Spotify... Esto puede tardar un momento.**")
                    songs = await fetch_spotify_playlist_tracks(url)
                    if not songs:
                        await ctx.send("🚫 **La playlist de Spotify está vacía o no se pudo procesar.**")
                        return
                    queues[ctx.guild.id].extend(songs)
                    await ctx.send(f"➕ **Añadida la playlist a la queue:** {len(songs)} canciones")
                    return
                else: # Es una canción
                    track_id = url.split("/")[-1].split("?")[0]
                    async with aiohttp.ClientSession() as session:
                        yt_link, title = await get_youtube_url_from_spotify_track(track_id, session)
                    if not yt_link:
                        await ctx.send("⚠️ **Error al obtener el enlace de YouTube desde Spotify.**")
                        return
                    queues[ctx.guild.id].append((yt_link, title))
                    await ctx.send(f"➕ **Añadida a la queue:** *{title}*")
                    return

            # Check if it's a playlist URL (not just a video with playlist parameters)
            if "playlist?list=" in url or ("list=" in url and "watch?v=" not in url):
                songs = await fetch_playlist_songs(url)
                if not songs:
                    await ctx.send("🚫 **La playlist de YouTube está vacía.**")
                    return
                queues[ctx.guild.id].extend(songs)
                await ctx.send(f"➕ **Añadida la playlist a la queue:** {len(songs)} canciones")
            else:
                # Check if it's a valid YouTube URL (supporting various formats)
                if not any(domain in url.lower() for domain in ['youtube.com', 'youtu.be', 'm.youtube.com']):
                    query_string = urllib.parse.urlencode({'search_query': url})
                    async with aiohttp.ClientSession() as session:
                        async with session.get(youtube_results_url + query_string) as response:
                            content = await response.text()
                            search_results = re.findall(r'/watch\?v=(.{11})', content)
                            if not search_results:
                                await ctx.send("⚠️ **No se encontró ningún resultado en YouTube.**")
                                return
                            url = youtube_base_url + 'watch?v=' + search_results[0]
                loop = asyncio.get_event_loop()
                data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
                title = data['title']
                queues[ctx.guild.id].append((url, title))
                await ctx.send(f"➕ **Añadida a la queue:** *{title}*")
        except Exception as e:
            logging.error(f"Error añadiendo canción a la queue: {e}")
            await ctx.send(f"⚠️ **Error al añadir la canción a la queue: {e}**")

    # Comando .queue ahora usa el paginador
    @client.command(name="queue", help="Muestra la queue actual.")
    async def show_queue(ctx):
        if not (ctx.guild.id in queues and queues[ctx.guild.id]):
            await ctx.send("🚫 **La queue está vacía!**")
            return

        items_per_page = 25
        total_songs = len(queues[ctx.guild.id])
        pages = [queues[ctx.guild.id][i:i + items_per_page] for i in range(0, len(queues[ctx.guild.id]), items_per_page)]

        if not pages:
            await ctx.send("🚫 **La queue está vacía!**")
            return

        paginator = QueuePaginator(ctx, pages, total_songs)
        
        # Deshabilitar botones si no son necesarios
        paginator.children[0].disabled = True
        if len(pages) <= 1:
            paginator.children[1].disabled = True

        initial_embed = paginator.create_embed()
        await ctx.send(embed=initial_embed, view=paginator)

    # ... (El resto de tus comandos: playnext, nowplaying, skip, etc. se mantienen igual)
    @client.command(name="playnext", help="Agrega la canción o playlist a la siguiente posición en la queue.")
    async def playnext(ctx, *, url):
        if not await ensure_voice(ctx):
            return
        if ctx.guild.id not in queues:
            queues[ctx.guild.id] = []
        try:
            if "spotify.com" in url:
                if "playlist" in url:
                    songs = await fetch_spotify_playlist_tracks(url)
                    if not songs:
                        await ctx.send("🚫 **La playlist de Spotify está vacía.**")
                        return
                    for song in reversed(songs):
                        queues[ctx.guild.id].insert(0, song)
                    await ctx.send(f"➕ **Añadida la playlist a la posición siguiente:** {len(songs)} canciones")
                    return
                else:
                    track_id = url.split("/")[-1].split("?")[0]
                    async with aiohttp.ClientSession() as session:
                        yt_link, title = await get_youtube_url_from_spotify_track(track_id, session)
                    if not yt_link:
                        await ctx.send("⚠️ **Error al obtener el enlace de YouTube desde Spotify.**")
                        return
                    url = yt_link

            # Check if it's a playlist URL (not just a video with playlist parameters)
            if "playlist?list=" in url or ("list=" in url and "watch?v=" not in url):
                songs = await fetch_playlist_songs(url)
                if not songs:
                    await ctx.send("🚫 **La playlist de YouTube está vacía.**")
                    return
                for song in reversed(songs):
                    queues[ctx.guild.id].insert(0, song)
                await ctx.send(f"➕ **Añadida la playlist a la posición siguiente:** {len(songs)} canciones")
            else:
                # Check if it's a valid YouTube URL (supporting various formats)
                if not any(domain in url.lower() for domain in ['youtube.com', 'youtu.be', 'm.youtube.com']):
                    query_string = urllib.parse.urlencode({'search_query': url})
                    async with aiohttp.ClientSession() as session:
                        async with session.get(youtube_results_url + query_string) as response:
                            content = await response.text()
                            search_results = re.findall(r'/watch\?v=(.{11})', content)
                            if not search_results:
                                await ctx.send("⚠️ **No se encontró ningún resultado en YouTube.**")
                                return
                            url = youtube_base_url + 'watch?v=' + search_results[0]
                loop = asyncio.get_event_loop()
                data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
                title = data['title']
                queues[ctx.guild.id].insert(0, (url, title))
                await ctx.send(f"➕ **{title} ha sido añadida como la siguiente canción!**")
        except Exception as e:
            logging.error(f"Error en playnext: {e}")
            await ctx.send(f"⚠️ **Error al agregar la canción a la posición siguiente: {e}**")

    def format_duration(seconds):
        if seconds == 0:
            return "N/A"
        minutes, seconds = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}" if hours > 0 else f"{minutes:02}:{seconds:02}"

    def parse_time_string(time_str):
        """
        Convierte strings de tiempo como '1m30s', '90s', '5m', '1:30' a segundos
        """
        try:
            time_str = time_str.lower().strip()
            total_seconds = 0
            
            # Formato MM:SS o HH:MM:SS
            if ':' in time_str:
                parts = time_str.split(':')
                if len(parts) == 2:  # MM:SS
                    minutes, seconds = map(int, parts)
                    total_seconds = minutes * 60 + seconds
                elif len(parts) == 3:  # HH:MM:SS
                    hours, minutes, seconds = map(int, parts)
                    total_seconds = hours * 3600 + minutes * 60 + seconds
                else:
                    return None
            else:
                # Formato con sufijos (5m, 30s, 1m30s)
                import re
                
                # Buscar horas (h)
                hours_match = re.search(r'(\d+)h', time_str)
                if hours_match:
                    total_seconds += int(hours_match.group(1)) * 3600
                    time_str = re.sub(r'\d+h', '', time_str)
                
                # Buscar minutos (m)
                minutes_match = re.search(r'(\d+)m', time_str)
                if minutes_match:
                    total_seconds += int(minutes_match.group(1)) * 60
                    time_str = re.sub(r'\d+m', '', time_str)
                
                # Buscar segundos (s)
                seconds_match = re.search(r'(\d+)s', time_str)
                if seconds_match:
                    total_seconds += int(seconds_match.group(1))
                    time_str = re.sub(r'\d+s', '', time_str)
                
                # Si queda algo que sea solo número, asumimos que son segundos
                remaining = re.sub(r'\s+', '', time_str)
                if remaining.isdigit():
                    total_seconds += int(remaining)
                elif remaining and not total_seconds:
                    # Si no se pudo parsear nada y queda texto
                    return None
            
            return total_seconds if total_seconds > 0 else None
            
        except (ValueError, AttributeError):
            return None

    def create_progress_bar(current, total, bar_length=15):
        if total == 0:
            return "─" * bar_length # Barra vacía si no hay duración
        progress = int((current / total) * bar_length)
        return "■" * progress + "─" * (bar_length - progress)

    # Reemplaza tu comando now_playing con este
    @client.command(name="nowplaying", help="Muestra la canción que está sonando ahora mismo.")
    async def now_playing(ctx):
        guild_id = ctx.guild.id
        if guild_id in song_data and voice_clients[guild_id].is_playing():
            data = song_data[guild_id]
            
            # Calcular tiempo transcurrido
            elapsed_time = (time.time() - data['start_time']) - data['paused_time']
            
            # Si está en pausa ahora mismo, también hay que contar ese tiempo
            if data['pause_start_time'] > 0:
                elapsed_time -= (time.time() - data['pause_start_time'])

            # Asegurarse de que el tiempo no exceda la duración
            elapsed_time = min(elapsed_time, data['duration'])

            # Formatear todo
            title = data['title']
            url = data['url']
            current_time_str = format_duration(elapsed_time)
            total_time_str = format_duration(data['duration'])
            progress_bar = create_progress_bar(elapsed_time, data['duration'])
            
            # Crear el embed
            embed = discord.Embed(
                title="🎵 Sonando Ahora",
                description=f"**[{title}]({url})**",
                color=discord.Color.green()
            )
            embed.add_field(
                name="",
                value=f"`{current_time_str} / {total_time_str}`\n`[{progress_bar}]`",
                inline=False
            )
            embed.set_footer(text=f"Pedido por {ctx.author.display_name}", icon_url=ctx.author.avatar)
            
            await ctx.send(embed=embed)
        else:
            logging.error("No hay canción sonando.")
            await ctx.send("🚫 **No hay ninguna canción sonando ahora mismo!**")

    @client.command(name="skip", help="Salta la canción actual.")
    async def skip(ctx):
        if not await ensure_voice(ctx):
            return
        if ctx.guild.id in voice_clients:
            logging.info("Saltando canción actual.")
            voice_clients[ctx.guild.id].stop()
            await ctx.send("⏭️ **Canción saltada!**")
        else:
            logging.error("No hay canción para saltar.")
            await ctx.send("🚫 **No hay ninguna canción reproduciéndose para saltar!**")

    @client.command(name="skipto", help="Salta a una canción específica en la queue, usando la posición.")
    async def skip_to(ctx, position: int):
        if ctx.guild.id in queues and len(queues[ctx.guild.id]) >= position > 0:
            # Detener la reproducción actual para saltar a la nueva canción
            if ctx.guild.id in voice_clients and voice_clients[ctx.guild.id].is_playing():
                voice_clients[ctx.guild.id].stop()

            # Mover la canción seleccionada al principio de la cola
            selected_song = queues[ctx.guild.id].pop(position - 1)
            queues[ctx.guild.id].insert(0, selected_song)
            
            await ctx.send(f"⏩ **Saltando a la canción número {position}: *{selected_song[1]}*!**")
            
            # play_next se encargará de reproducir la siguiente canción en la cola (que ahora es la que elegimos)
            # No es necesario llamar a play_song directamente si after_play está bien configurado
        else:
            await ctx.send("🚫 **Posición inválida en la queue.**")


    @client.command(name="clear", help="Limpia la queue actual.")
    async def clear_queue(ctx):
        if not await ensure_voice(ctx):
            return
        if ctx.guild.id in queues:
            logging.info("Limpiando la queue.")
            queues[ctx.guild.id].clear()
            await ctx.send("🧹 **Se limpió la cola de canciones!**")
        else:
            logging.error("No hay cola que limpiar.")
            await ctx.send("🚫 **No hay cola que limpiar!**")

    @client.command(name="pause", help="Pausa la reproducción de la canción actual.")
    async def pause(ctx):
        if not await ensure_voice(ctx):
            return
        if ctx.guild.id in voice_clients and voice_clients[ctx.guild.id].is_playing():
            logging.info("Pausando reproducción.")
            voice_clients[ctx.guild.id].pause()
            
            if ctx.guild.id in song_data:
                song_data[ctx.guild.id]['pause_start_time'] = time.time()

            await ctx.send("⏸️ **Reproducción pausada!**")
        else:
            logging.error("No hay nada reproduciéndose para pausar.")
            await ctx.send("🚫 **No hay nada reproduciéndose para pausar!**")

    @client.command(name="resume", help="Reanuda la reproducción si está pausada.")
    async def resume(ctx):
        if not await ensure_voice(ctx):
            return
        if ctx.guild.id in voice_clients and voice_clients[ctx.guild.id].is_paused():
            logging.info("Reanudando reproducción.")
            voice_clients[ctx.guild.id].resume()
            
            # --- AÑADIR ESTO ---
            if ctx.guild.id in song_data and song_data[ctx.guild.id]['pause_start_time'] > 0:
                paused_duration = time.time() - song_data[ctx.guild.id]['pause_start_time']
                song_data[ctx.guild.id]['paused_time'] += paused_duration
                song_data[ctx.guild.id]['pause_start_time'] = 0
            # --- FIN ---

            await ctx.send("▶️ **Reproducción reanudada!**")
        else:
            logging.error("No hay reproducción pausada para reanudar.")
            await ctx.send("🚫 **No hay nada pausado para reanudar!**")

    @client.command(name="loop", help="Activa o desactiva el loop de la canción actual.")
    async def loop_cmd(ctx):
        if not await ensure_voice(ctx):
            return
        loop_status[ctx.guild.id] = not loop_status.get(ctx.guild.id, False)
        if loop_status[ctx.guild.id]:
            await ctx.send("🔁 **Loop activado!**")
            logging.info(f"Loop activado en el servidor {ctx.guild.id}.")
        else:
            await ctx.send("🔁 **Loop desactivado!**")
            logging.info(f"Loop desactivado en el servidor {ctx.guild.id}.")

    @client.command(name="stop", help="Detiene la reproducción y limpia la queue.")
    async def stop(ctx):
        if not await ensure_voice(ctx):
            return
        if ctx.guild.id in voice_clients:
            logging.info("Deteniendo la reproducción y limpiando la queue.")
            manual_stop[ctx.guild.id] = True # Marcar para que after_play no continúe
            voice_clients[ctx.guild.id].stop()
            if ctx.guild.id in queues:
                queues[ctx.guild.id].clear()
            await update_presence(False, "Nada sonando")
            await ctx.send("⏹️ **Reproducción detenida!**")
        else:
            logging.error("No hay canción reproduciéndose para detener.")
            await ctx.send("🚫 **No hay ninguna canción sonando!**")

    @client.command(name="shuffle", help="Mezcla aleatoriamente las canciones en la queue.")
    async def shuffle(ctx):
        if ctx.guild.id in queues and queues[ctx.guild.id]:
            random.shuffle(queues[ctx.guild.id])
            logging.info("Queue mezclada.")
            await ctx.send("🔀 **Queue mezclada!**")
        else:
            logging.error("La queue está vacía para mezclar.")
            await ctx.send("🚫 **La queue está vacía!**")

    @client.command(name="seek", help="Salta a un timestamp específico de la canción (ej: 1m30s, 90s, 2:15)")
    async def seek(ctx, *, time_input):
        if not await ensure_voice(ctx):
            return
            
        guild_id = ctx.guild.id
        
        # Verificar que hay una canción reproduciéndose
        if guild_id not in voice_clients or not voice_clients[guild_id].is_connected():
            await ctx.send("🚫 **No estoy conectado a un canal de voz.**")
            return
            
        if not voice_clients[guild_id].is_playing() and not voice_clients[guild_id].is_paused():
            await ctx.send("🚫 **No hay ninguna canción reproduciéndose.**")
            return
            
        if guild_id not in song_data:
            await ctx.send("🚫 **No hay información de la canción actual.**")
            return
            
        # Parsear el tiempo
        seek_seconds = parse_time_string(time_input)
        if seek_seconds is None:
            await ctx.send("⚠️ **Formato de tiempo inválido. Usa formatos como: 1m30s, 90s, 2:15, 1:02:30**")
            return
            
        # Verificar que el tiempo está dentro de la duración de la canción
        song_duration = song_data[guild_id]['duration']
        if seek_seconds >= song_duration:
            formatted_duration = format_duration(song_duration)
            await ctx.send(f"⚠️ **El tiempo especificado ({format_duration(seek_seconds)}) excede la duración de la canción ({formatted_duration}).**")
            return
            
        # Reiniciar la canción desde el timestamp especificado
        try:
            current_url = song_data[guild_id]['url']
            current_title = song_data[guild_id]['title']
            
            # Marcar que estamos haciendo seek para evitar el mensaje de queue vacía
            seek_in_progress[guild_id] = True
            
            # Detener la reproducción actual
            voice_clients[guild_id].stop()
            
            # Actualizar el start_time para reflejar el seek
            song_data[guild_id]['start_time'] = time.time() - seek_seconds
            song_data[guild_id]['paused_time'] = 0
            song_data[guild_id]['pause_start_time'] = 0
            
            # Extraer información de la canción con seek
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(current_url, download=False))
            stream_url = data['url']
            
            # Configurar FFmpeg para comenzar desde el timestamp especificado
            seek_ffmpeg_options = {
                'before_options': f'-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -ss {seek_seconds}',
                'options': '-vn -filter:a "volume=0.375"'  # Mismo volumen que en play_song
            }

            # Reproducir desde el timestamp usando FFmpegOpusAudio
            player = discord.FFmpegOpusAudio(stream_url, **seek_ffmpeg_options)
            voice_clients[guild_id].play(player, after=after_play(ctx))
            
            seek_time_str = format_duration(seek_seconds)
            await ctx.send(f"⏩ **Saltando a {seek_time_str} en:** *{current_title}*")
            
        except Exception as e:
            # Resetear la bandera en caso de error
            seek_in_progress[guild_id] = False
            logging.error(f"Error en seek: {e}")
            await ctx.send(f"⚠️ **Error al hacer seek: {e}**")

    
    @client.command(name="move", help="Mueve una canción de una posición a otra en la queue.")
    async def move(ctx, from_pos: int, to_pos: int):
        if ctx.guild.id not in queues or not queues[ctx.guild.id]:
            await ctx.send("🚫 **La queue está vacía!**")
            return

        queue_len = len(queues[ctx.guild.id])
        if not (1 <= from_pos <= queue_len and 1 <= to_pos <= queue_len):
            await ctx.send(f"🚫 **Las posiciones deben estar dentro del rango de la queue (1 a {queue_len}).**")
            return

        if from_pos == to_pos:
            await ctx.send("ℹ️ **La canción ya está en esa posición.**")
            return

        song = queues[ctx.guild.id].pop(from_pos - 1)
        queues[ctx.guild.id].insert(to_pos - 1, song)
        await ctx.send(f"🔀 **Movida *{song[1]}* de la posición {from_pos} a la {to_pos}.**")

    @client.command(name="commands", help="Muestra una lista personalizada de comandos.")
    async def show_commands(ctx):
        embed = discord.Embed(title="Comandos disponibles", color=discord.Color.blue())
        embed.add_field(name=".play <enlace>",     value="Reproduce una canción o playlist desde YouTube o Spotify.", inline=False)
        embed.add_field(name=".add <enlace>",      value="Añade una canción o playlist a la queue.", inline=False)
        embed.add_field(name=".playnext <enlace>", value="Agrega la canción a la siguiente posición en la queue.", inline=False)
        embed.add_field(name=".queue",             value="Muestra la queue actual.", inline=False)
        embed.add_field(name=".nowplaying",        value="Muestra la canción que está sonando ahora mismo.", inline=False)
        embed.add_field(name=".skip",              value="Salta la canción actual.", inline=False)
        embed.add_field(name=".skipto <posición>", value="Salta a una canción específica en la queue.", inline=False)
        embed.add_field(name=".seek <tiempo>",     value="Salta a un timestamp específico (ej: 1m30s, 90s, 2:15).", inline=False)
        embed.add_field(name=".move <de> <a>",       value="Mueve una canción de una posición a otra en la queue.", inline=False)
        embed.add_field(name=".clear",             value="Limpia la queue actual.", inline=False)
        embed.add_field(name=".pause",             value="Pausa la reproducción de la canción actual.", inline=False)
        embed.add_field(name=".resume",            value="Reanuda la reproducción si está pausada.", inline=False)
        embed.add_field(name=".loop",              value="Activa o desactiva el loop de la canción actual.", inline=False)
        embed.add_field(name=".stop",              value="Detiene la reproducción y limpia la queue.", inline=False)
        embed.add_field(name=".shuffle",           value="Mezcla aleatoriamente las canciones en la queue.", inline=False)
        embed.add_field(name=".leave",             value="Desconecta el bot del canal de voz y borra la queue.", inline=False)
        await ctx.send(embed=embed)

    @client.command(name="leave", help="Desconecta el bot del canal de voz y borra la queue.")
    async def leave(ctx):
        if ctx.guild.id in voice_clients:
            await voice_clients[ctx.guild.id].disconnect()
            del voice_clients[ctx.guild.id]
            if ctx.guild.id in queues:
                queues[ctx.guild.id].clear()
            await ctx.send("👋 **Me he desconectado del canal de voz y la queue ha sido borrada.**")
        else:
            await ctx.send("🚫 **No estoy conectado a ningún canal de voz.**")

    @client.event
    async def on_command_error(ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            if ctx.command.name == "move":
                await ctx.send(f"⚠️ **Faltan argumentos. Usa: `{ctx.prefix}move <de> <a_>`**")
            else:
                await ctx.send(f"⚠️ **Falta el enlace o nombre de la canción. Usa: `{ctx.prefix}{ctx.command.name} <canción>`**")
        elif isinstance(error, commands.CommandInvokeError):
            logging.error(f"Error ejecutando comando {ctx.command.name}: {error.original}")
            # Evitamos enviar el error de embed grande al chat
            if isinstance(error.original, discord.HTTPException) and error.original.code == 50035:
                logging.error("Error de Embed: El contenido era demasiado grande.")
            else:
                await ctx.send(f"🔥 **Ocurrió un error inesperado al ejecutar el comando.**")
        else:
            logging.error(f"Error no manejado: {error}")


    async def shutdown():
        for vc in voice_clients.values():
            await vc.disconnect()
        await client.close()

    try:
        await client.start(TOKEN)
    except KeyboardInterrupt:
        print("Apagando bot...")
        await shutdown()
        print("Bot apagado correctamente.")

def start_bot():
    """Iniciar el bot en un thread separado"""
    asyncio.run(run_bot())

if __name__ == "__main__":
    # Iniciar el bot de Discord en un thread separado
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()

    # Iniciar el icono del system tray en un thread separado
    tray_thread = threading.Thread(target=log_window.run_tray, daemon=True)
    tray_thread.start()

    # Ejecutar la ventana de logs en el thread principal (requerido por tkinter en Windows)
    log_window.run()