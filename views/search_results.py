"""
Vista de resultados de búsqueda con botones para elegir
"""
import discord
import logging

from core.config import SEARCH_VIEW_TIMEOUT


class SearchResultsView(discord.ui.View):
    """Vista con botones para seleccionar un resultado de búsqueda"""

    def __init__(self, ctx, results: list, on_select_callback, timeout=SEARCH_VIEW_TIMEOUT):
        """
        Args:
            ctx: Contexto del comando
            results: Lista de tuplas (url, title, duration) o (url, title)
            on_select_callback: Función async a llamar cuando se selecciona un resultado
            timeout: Tiempo en segundos antes de que expire la vista
        """
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.results = results
        self.on_select_callback = on_select_callback
        self.message = None
        self.selected = False

        # Crear botones dinámicamente para cada resultado
        for i, result in enumerate(results):
            button = discord.ui.Button(
                label=str(i + 1),
                style=discord.ButtonStyle.primary,
                custom_id=f"search_result_{i}"
            )
            button.callback = self.create_callback(i)
            self.add_item(button)

        # Botón de cancelar
        cancel_button = discord.ui.Button(
            label="Cancelar",
            style=discord.ButtonStyle.danger,
            custom_id="search_cancel"
        )
        cancel_button.callback = self.cancel_callback
        self.add_item(cancel_button)

    def create_callback(self, index: int):
        """Crea un callback para el botón de selección"""
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.ctx.author.id:
                await interaction.response.send_message(
                    "Solo quien hizo la búsqueda puede seleccionar.",
                    ephemeral=True
                )
                return

            self.selected = True
            result = self.results[index]
            url = result[0]
            title = result[1]
            duration = result[2] if len(result) > 2 else 0

            # Deshabilitar todos los botones
            for item in self.children:
                item.disabled = True

            await interaction.response.edit_message(
                content=f"**Seleccionado:** *{title}*",
                embed=None,
                view=self
            )

            # Llamar al callback con la selección (incluyendo duración)
            await self.on_select_callback(self.ctx, url, title, duration)

        return callback

    async def cancel_callback(self, interaction: discord.Interaction):
        """Callback para el botón de cancelar"""
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                "Solo quien hizo la búsqueda puede cancelar.",
                ephemeral=True
            )
            return

        self.selected = True

        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content="**Búsqueda cancelada.**",
            embed=None,
            view=self
        )

    async def on_timeout(self):
        """Deshabilitar botones cuando expira el tiempo"""
        if self.selected:
            return

        for item in self.children:
            item.disabled = True

        try:
            if self.message:
                await self.message.edit(
                    content="**Búsqueda expirada.** Usa `.search` de nuevo.",
                    embed=None,
                    view=self
                )
        except Exception as e:
            logging.debug(f"Error al actualizar mensaje expirado: {e}")


def create_search_embed(query: str, results: list) -> discord.Embed:
    """
    Crea el embed con los resultados de búsqueda

    Args:
        query: Término de búsqueda original
        results: Lista de tuplas (url, title, duration) o (url, title)

    Returns:
        discord.Embed con los resultados formateados
    """
    embed = discord.Embed(
        title=f"Resultados para: {query}",
        description="Selecciona un número para reproducir:",
        color=discord.Color.blue()
    )

    for i, result in enumerate(results):
        url = result[0]
        title = result[1]
        # Truncar títulos muy largos
        display_title = title if len(title) <= 60 else title[:57] + "..."
        embed.add_field(
            name=f"{i + 1}. {display_title}",
            value=f"[Ver en YouTube]({url})",
            inline=False
        )

    embed.set_footer(text="Los botones expiran en 60 segundos")
    return embed
