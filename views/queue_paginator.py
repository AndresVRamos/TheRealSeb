"""
Vista de paginación para la queue de canciones
"""
import discord


class QueuePaginator(discord.ui.View):
    """Paginador con botones para navegar la queue"""

    def __init__(self, ctx, pages, total_songs, items_per_page=10):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.pages = pages
        self.total_songs = total_songs
        self.current_page = 0
        self.total_pages = len(pages)
        self.items_per_page = items_per_page

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
