"""
Vista de paginación para la queue de canciones
"""
import discord
from core.config import QUEUE_VIEW_TIMEOUT
from core.formatters import format_duration


class QueuePaginator(discord.ui.View):
    """Paginador con botones para navegar la queue"""

    def __init__(self, ctx, pages, total_songs, items_per_page=10, current_song_remaining=0, total_duration=0):
        super().__init__(timeout=QUEUE_VIEW_TIMEOUT)
        self.ctx = ctx
        self.pages = pages
        self.total_songs = total_songs
        self.current_page = 0
        self.total_pages = len(pages)
        self.items_per_page = items_per_page
        self.current_song_remaining = current_song_remaining  # Tiempo restante de canción actual
        self.total_duration = total_duration  # Duración total de la queue

    def _format_song_duration(self, duration):
        """Formatea la duración de una canción"""
        if duration is None or duration == 0:
            return "?"
        return format_duration(duration)

    def _calculate_time_until(self, song_index):
        """Calcula el tiempo estimado hasta que toque una canción"""
        # Empezar con el tiempo restante de la canción actual
        time_until = self.current_song_remaining

        # Sumar duraciones de canciones anteriores en la queue
        song_count = 0
        for page in self.pages:
            for song in page:
                if song_count >= song_index:
                    return time_until
                duration = song[3] if len(song) > 3 else 0
                if duration and duration > 0:
                    time_until += duration
                song_count += 1

        return time_until

    def create_embed(self):
        page_content = self.pages[self.current_page]
        start_index = self.current_page * self.items_per_page

        queue_list = []
        for i, song in enumerate(page_content):
            song_index = i + start_index
            title = song[1]
            duration = song[3] if len(song) > 3 else 0
            duration_str = self._format_song_duration(duration)

            # Calcular tiempo estimado hasta esta canción
            time_until = self._calculate_time_until(song_index)
            if time_until > 0:
                time_until_str = format_duration(time_until)
                queue_list.append(f"**{song_index + 1}.** *{title}* `[{duration_str}]` — en ~{time_until_str}")
            else:
                queue_list.append(f"**{song_index + 1}.** *{title}* `[{duration_str}]`")

        description = "\n".join(queue_list)

        embed = discord.Embed(
            title=f"Queue Actual (Página {self.current_page + 1}/{self.total_pages})",
            description=description,
            color=discord.Color.blurple()
        )

        # Footer con duración total
        if self.total_duration > 0:
            total_duration_str = format_duration(self.total_duration)
            embed.set_footer(text=f"Total: {self.total_songs} canciones • Duración total: {total_duration_str}")
        else:
            embed.set_footer(text=f"Total: {self.total_songs} canciones")

        return embed

    async def update_message(self, interaction: discord.Interaction):
        self.children[0].disabled = self.current_page == 0
        self.children[1].disabled = self.current_page >= self.total_pages - 1

        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Anterior", emoji="⬅️", style=discord.ButtonStyle.secondary, custom_id="prev_page")
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("No puedes usar estos botones!", ephemeral=True)
            return

        if self.current_page > 0:
            self.current_page -= 1
            await self.update_message(interaction)

    @discord.ui.button(label="Siguiente", emoji="➡️", style=discord.ButtonStyle.secondary, custom_id="next_page")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("No puedes usar estos botones!", ephemeral=True)
            return

        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            await self.update_message(interaction)
