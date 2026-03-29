"""
Controles interactivos de música con botones para el comando nowplaying
"""
import discord
import time
import logging
import asyncio

from core.config import MUSIC_CONTROLS_TIMEOUT, NOWPLAYING_UPDATE_INTERVAL, AUTOPLAY_ENABLED
from core.formatters import format_duration, create_progress_bar
from core.playback import (
    pause_playback,
    resume_playback,
    skip_song,
    toggle_loop,
    toggle_autoplay,
    shuffle_queue,
    stop_playback
)


def create_now_playing_embed(song_data, queues, loop_status, guild_id, author=None, song_finished=False, autoplay_status=None):
    """
    Crea el embed de 'Sonando Ahora' con la información de la canción actual.

    Args:
        song_data: Diccionario con datos de canciones por guild
        queues: Diccionario con colas por guild
        loop_status: Diccionario con estado de loop por guild
        guild_id: ID del servidor
        author: Usuario fallback
        song_finished: Si True, muestra el tiempo como igual a la duración total
        autoplay_status: Diccionario con estado de autoplay por guild

    Returns:
        discord.Embed con la información de la canción
    """
    if guild_id not in song_data:
        return discord.Embed(
            title="🚫 No hay canción",
            description="No hay ninguna canción reproduciéndose ahora mismo.",
            color=discord.Color.red()
        )

    data = song_data[guild_id]

    requester = data.get('requester', author)

    # Calcular tiempo transcurrido
    if song_finished:
        elapsed_time = data['duration']
    else:
        elapsed_time = (time.time() - data['start_time']) - data['paused_time']
        if data['pause_start_time'] > 0:
            elapsed_time -= (time.time() - data['pause_start_time'])
        elapsed_time = max(0, min(elapsed_time, data['duration']))

    title = data['title']
    url = data['url']
    current_time_str = format_duration(elapsed_time)
    total_time_str = format_duration(data['duration'])
    progress_bar = create_progress_bar(elapsed_time, data['duration'])

    embed = discord.Embed(
        title="🎵 Sonando Ahora",
        description=f"**[{title}]({url})**",
        color=discord.Color.red()
    )
    embed.add_field(
        name="",
        value=f"`{current_time_str} / {total_time_str}`\n`[{progress_bar}]`",
        inline=False
    )

    thumbnail = data.get('thumbnail')
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)

    # Mostrar siguiente canción si hay queue
    if guild_id in queues and queues[guild_id]:
        next_song = queues[guild_id][0][1]
        queue_count = len(queues[guild_id])
        embed.add_field(
            name="⏭️ Siguiente",
            value=f"{next_song}\n*+{queue_count - 1} más en la cola*" if queue_count > 1 else next_song,
            inline=False
        )

    # Footer con estado de loop y autoplay
    if requester:
        status_parts = []
        if loop_status.get(guild_id, False):
            status_parts.append("🔁 Loop")
        if song_data.get(guild_id, {}).get('is_autoplay', False):
            status_parts.append("📻 Radio")

        if status_parts:
            status_text = " | ".join(status_parts)
            embed.set_footer(
                text=f"{status_text} | Pedido por {requester.display_name}",
                icon_url=requester.avatar
            )
        else:
            embed.set_footer(
                text=f"Pedido por {requester.display_name}",
                icon_url=requester.avatar
            )

    return embed


class MusicControls(discord.ui.View):
    """Vista con botones de control de reproducción"""

    def __init__(self, ctx, message, voice_clients, loop_status, queues, song_data, manual_stop, bot=None, autoplay_status=None):
        super().__init__(timeout=MUSIC_CONTROLS_TIMEOUT)
        self.ctx = ctx
        self.message = message
        self.voice_clients = voice_clients
        self.loop_status = loop_status
        self.autoplay_status = autoplay_status if autoplay_status is not None else {}
        self.queues = queues
        self.song_data = song_data
        self.manual_stop = manual_stop
        self.guild_id = ctx.guild.id
        self.bot = bot
        self.update_task = None  # Tarea de actualización del embed

        # Remover botón de autoplay si está deshabilitado globalmente
        if not AUTOPLAY_ENABLED:
            self.remove_item(self.autoplay_button)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Verificar que el usuario esté en el mismo canal de voz que el bot"""
        if not interaction.user.voice:
            await interaction.response.send_message(
                "🚫 **Debes estar en un canal de voz para usar estos botones!**",
                ephemeral=True
            )
            return False

        if interaction.user.voice.channel != self.ctx.guild.voice_client.channel:
            await interaction.response.send_message(
                "🚫 **Debes estar en el mismo canal de voz que el bot!**",
                ephemeral=True
            )
            return False

        return True

    async def on_timeout(self):
        """Deshabilitar todos los botones cuando ocurre el timeout"""
        self.cancel_update_loop()
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(view=self)
        except:
            pass

    def start_update_loop(self):
        """Inicia el loop de actualización del embed cada 15 segundos"""
        if self.update_task is None or self.update_task.done():
            self.update_task = asyncio.create_task(self._update_loop())

    def cancel_update_loop(self):
        """Cancela el loop de actualización"""
        if self.update_task and not self.update_task.done():
            self.update_task.cancel()
            self.update_task = None

    async def _update_loop(self):
        """Loop interno que actualiza el embed periódicamente"""
        try:
            while True:
                await asyncio.sleep(NOWPLAYING_UPDATE_INTERVAL)

                # Verificar si todavía está reproduciendo
                if (self.guild_id not in self.voice_clients or
                    not self.voice_clients[self.guild_id].is_connected() or
                    not (self.voice_clients[self.guild_id].is_playing() or
                         self.voice_clients[self.guild_id].is_paused())):
                    break

                if not self.message:
                    break

                # Actualizar el embed
                try:
                    embed = create_now_playing_embed(
                        self.song_data, self.queues, self.loop_status,
                        self.guild_id, self.ctx.author, autoplay_status=self.autoplay_status
                    )
                    self.update_button_states()
                    await self.message.edit(embed=embed, view=self)
                except Exception as e:
                    logging.debug(f"Error actualizando embed: {e}")
                    break

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logging.debug(f"Error en _update_loop: {e}")

    def _get_button(self, custom_id: str):
        """Obtiene un botón por su custom_id"""
        for item in self.children:
            if hasattr(item, 'custom_id') and item.custom_id == custom_id:
                return item
        return None

    def update_button_states(self):
        """Actualizar estados de botones según el estado actual de reproducción"""
        guild_id = self.guild_id

        if (guild_id not in self.voice_clients or
                not self.voice_clients[guild_id].is_connected()):
            for item in self.children:
                item.disabled = True
            return

        vc = self.voice_clients[guild_id]

        # Pause/Resume
        pause_btn = self._get_button("pause_resume")
        if pause_btn:
            if vc.is_playing():
                pause_btn.emoji = "⏸️"
                pause_btn.label = "Pausar"
                pause_btn.disabled = False
            elif vc.is_paused():
                pause_btn.emoji = "▶️"
                pause_btn.label = "Reanudar"
                pause_btn.disabled = False
            else:
                pause_btn.disabled = True

        # Skip
        skip_btn = self._get_button("skip")
        if skip_btn:
            skip_btn.disabled = not (vc.is_playing() or vc.is_paused())

        # Loop
        loop_btn = self._get_button("loop")
        if loop_btn:
            if self.loop_status.get(guild_id, False):
                loop_btn.style = discord.ButtonStyle.success
                loop_btn.label = "Loop: ON"
            else:
                loop_btn.style = discord.ButtonStyle.secondary
                loop_btn.label = "Loop: OFF"

        # Autoplay/Radio (solo si existe el botón)
        autoplay_btn = self._get_button("autoplay")
        if autoplay_btn:
            if self.autoplay_status.get(guild_id, False):
                autoplay_btn.style = discord.ButtonStyle.success
                autoplay_btn.label = "Radio: ON"
            else:
                autoplay_btn.style = discord.ButtonStyle.secondary
                autoplay_btn.label = "Radio: OFF"

        # Shuffle
        shuffle_btn = self._get_button("shuffle")
        if shuffle_btn:
            queue_len = len(self.queues.get(guild_id, []))
            shuffle_btn.disabled = queue_len < 2

        # Stop
        stop_btn = self._get_button("stop")
        if stop_btn:
            stop_btn.disabled = False

    def _get_status_embed(self):
        """Obtiene el embed del estado actual: canción sonando o mensaje de error si no hay reproducción"""
        guild_id = self.guild_id

        # Verificar si hay reproducción activa
        if (guild_id not in self.voice_clients or
                not (self.voice_clients[guild_id].is_playing() or
                     self.voice_clients[guild_id].is_paused())):
            return discord.Embed(
                title="🚫 No hay canción",
                description="No hay ninguna canción reproduciéndose ahora mismo.",
                color=discord.Color.red()
            )

        return create_now_playing_embed(
            self.song_data, self.queues, self.loop_status,
            guild_id, self.ctx.author, autoplay_status=self.autoplay_status
        )

    async def update_embed(self, interaction: discord.Interaction):
        """Actualizar el embed con información actual"""
        embed = self._get_status_embed()
        self.update_button_states()
        await interaction.response.edit_message(embed=embed, view=self)

    async def update_embed_after_response(self, interaction: discord.Interaction):
        """Actualizar embed después de ya haber enviado una respuesta ephemeral"""
        embed = self._get_status_embed()
        self.update_button_states()
        await self.message.edit(embed=embed, view=self)

    @discord.ui.button(label="Pausar", emoji="⏸️", style=discord.ButtonStyle.primary, custom_id="pause_resume")
    async def pause_resume_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = self.guild_id
        vc = self.voice_clients.get(guild_id)

        if not vc or not vc.is_connected():
            await interaction.response.send_message("🚫 **No estoy conectado a un canal de voz.**", ephemeral=True)
            return

        if vc.is_playing():
            await pause_playback(guild_id, self.song_data, self.voice_clients)
            logging.info(f"Reproducción pausada vía botón por {interaction.user}")
        elif vc.is_paused():
            await resume_playback(guild_id, self.song_data, self.voice_clients)
            logging.info(f"Reproducción reanudada vía botón por {interaction.user}")
        else:
            await interaction.response.send_message("🚫 **No hay nada reproduciéndose.**", ephemeral=True)
            return

        await self.update_embed(interaction)

    @discord.ui.button(label="Skip", emoji="⏭️", style=discord.ButtonStyle.secondary, custom_id="skip")
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = self.guild_id

        if await skip_song(guild_id, self.voice_clients):
            logging.info(f"Canción saltada vía botón por {interaction.user}")
            await interaction.response.send_message("⏭️ **Canción saltada!**", ephemeral=True)
        else:
            await interaction.response.send_message("🚫 **No hay ninguna canción para saltar.**", ephemeral=True)

    @discord.ui.button(label="Loop: OFF", emoji="🔁", style=discord.ButtonStyle.secondary, custom_id="loop")
    async def loop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = self.guild_id

        is_looping = toggle_loop(guild_id, self.loop_status)

        if is_looping:
            logging.info(f"Loop activado vía botón por {interaction.user}")
            await interaction.response.send_message("🔁 **Loop activado!**", ephemeral=True)
        else:
            logging.info(f"Loop desactivado vía botón por {interaction.user}")
            await interaction.response.send_message("🔁 **Loop desactivado!**", ephemeral=True)

        await self.update_embed_after_response(interaction)

    @discord.ui.button(label="Radio: OFF", emoji="📻", style=discord.ButtonStyle.secondary, custom_id="autoplay")
    async def autoplay_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = self.guild_id

        is_autoplay = toggle_autoplay(guild_id, self.autoplay_status)

        if is_autoplay:
            logging.info(f"Autoplay activado vía botón por {interaction.user}")
            await interaction.response.send_message("📻 **Radio activado!** Cuando termine la queue, se reproducirán canciones parecidas.", ephemeral=True)
        else:
            logging.info(f"Autoplay desactivado vía botón por {interaction.user}")
            await interaction.response.send_message("📻 **Radio desactivado.**", ephemeral=True)

        await self.update_embed_after_response(interaction)

    @discord.ui.button(label="Shuffle", emoji="🔀", style=discord.ButtonStyle.secondary, custom_id="shuffle")
    async def shuffle_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = self.guild_id

        if await shuffle_queue(guild_id, self.queues):
            queue_len = len(self.queues[guild_id])
            logging.info(f"Queue mezclada vía botón por {interaction.user}")
            await interaction.response.send_message(f"🔀 **Queue mezclada!** ({queue_len} canciones)", ephemeral=True)
            await self.update_embed_after_response(interaction)
        else:
            await interaction.response.send_message("🚫 **La queue necesita al menos 2 canciones para mezclar.**", ephemeral=True)

    @discord.ui.button(label="Stop", emoji="⏹️", style=discord.ButtonStyle.danger, custom_id="stop")
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = self.guild_id

        # Cancelar tarea de actualización del embed
        self.cancel_update_loop()

        if await stop_playback(guild_id, self.voice_clients, self.queues, self.manual_stop, bot=self.bot):
            logging.info(f"Reproducción detenida vía botón por {interaction.user}")
            await interaction.response.send_message("⏹️ **Reproducción detenida y queue limpiada!**", ephemeral=True)
        else:
            await interaction.response.send_message("🚫 **No estoy conectado a un canal de voz.**", ephemeral=True)
