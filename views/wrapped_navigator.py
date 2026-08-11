"""
Vista interactiva de navegación para Wrapped en The Real Seb bot
Permite navegar entre diferentes secciones estilo Instagram Stories
"""
import discord
from typing import Dict, Any, List

from core.config import WRAPPED_VIEW_TIMEOUT, SPOTIFY_GREEN_RGB
from core.wrapped import (
    create_intro_section,
    create_top_songs_section,
    create_top_artists_section,
    create_stats_section,
    create_timeline_section,
    create_achievements_section,
    create_fun_facts_section,
    create_rankings_section,
    create_only_you_section
)


class WrappedNavigator(discord.ui.View):
    """
    Vista de navegación interactiva para Wrapped.

    Secciones:
    0. Intro - Resumen general y personalidad
    1. Top Songs - Top 5 canciones
    2. Top Artists - Top 5 artistas
    3. Stats - Estadísticas y récords
    4. Timeline - Eventos mes a mes
    5. Achievements - Badges desbloqueados
    6. Fun Facts - Comparaciones creativas
    7. Rankings - Posición en servidor
    8. Solo Tú - Canciones únicas
    """

    SECTIONS = [
        "Intro", "Top Songs", "Top Artists", "Stats",
        "Timeline", "Achievements", "Fun Facts", "Rankings", "Solo Tú"
    ]

    def __init__(self, ctx_or_interaction, user: discord.Member, stats: Dict[str, Any],
                 extended_data: Dict[str, Any], message: discord.Message = None):
        super().__init__(timeout=WRAPPED_VIEW_TIMEOUT)
        self.ctx = ctx_or_interaction  # Puede ser ctx (prefix) o interaction (slash)
        self.user = user
        self.guild = ctx_or_interaction.guild  # Ambos tienen .guild
        # Obtener el invocador (quien ejecutó el comando)
        self.invoker = getattr(ctx_or_interaction, 'author', None) or getattr(ctx_or_interaction, 'user', None)
        self.stats = stats
        self.extended_data = extended_data
        self.current_section = 0
        self.message = message

        # Generar todos los embeds al inicio (caché)
        self.embeds = self._generate_all_embeds()

        # Actualizar estado de botones
        self._update_buttons()

    def _generate_all_embeds(self) -> List[discord.Embed]:
        """Genera los 9 embeds de todas las secciones"""
        try:
            embeds = [
                create_intro_section(self.user, self.stats, self.guild),
                create_top_songs_section(self.user, self.stats, self.guild),
                create_top_artists_section(self.user, self.stats, self.guild),
                create_stats_section(self.user, self.stats, self.extended_data, self.guild),
                create_timeline_section(self.user, self.stats, self.extended_data, self.guild),
                create_achievements_section(self.user, self.stats, self.extended_data, self.guild),
                create_fun_facts_section(self.user, self.stats, self.extended_data, self.guild),
                create_rankings_section(self.user, self.stats, self.extended_data, self.guild),
                create_only_you_section(self.user, self.stats, self.extended_data, self.guild)
            ]
            return embeds
        except Exception as e:
            # Fallback a embed simple si hay error
            error_embed = discord.Embed(
                title="⚠️ Error al generar Wrapped",
                description=f"Ocurrió un error: {str(e)}",
                color=discord.Color.red()
            )
            return [error_embed]

    def _update_buttons(self):
        """Actualiza el estado de los botones de navegación"""
        # Botones de navegación (anterior/siguiente)
        self.children[0].disabled = (self.current_section == 0)
        self.children[1].disabled = (self.current_section >= len(self.SECTIONS) - 1)

        # Actualizar label del botón indicador de sección
        section_name = self.SECTIONS[self.current_section]
        section_num = self.current_section + 1
        total_sections = len(self.SECTIONS)
        self.children[2].label = f"📍 {section_name} ({section_num}/{total_sections})"

    async def update_message(self, interaction: discord.Interaction):
        """Actualiza el mensaje con la sección actual"""
        self._update_buttons()
        embed = self.embeds[self.current_section]
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="◀ Anterior", style=discord.ButtonStyle.primary, row=0)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.invoker:
            await interaction.response.send_message(
                "🚫 No puedes usar estos botones!",
                ephemeral=True
            )
            return

        if self.current_section > 0:
            self.current_section -= 1
            await self.update_message(interaction)

    @discord.ui.button(label="Siguiente ▶", style=discord.ButtonStyle.primary, row=0)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.invoker:
            await interaction.response.send_message(
                "🚫 No puedes usar estos botones!",
                ephemeral=True
            )
            return

        if self.current_section < len(self.SECTIONS) - 1:
            self.current_section += 1
            await self.update_message(interaction)

    @discord.ui.button(label="📍 Sección", style=discord.ButtonStyle.secondary, row=0, disabled=True)
    async def section_indicator(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass  # Solo indicador, no hace nada

    # === BOTONES DE ACCESO RÁPIDO (fila 2) ===

    @discord.ui.button(emoji="🎵", label="Songs", style=discord.ButtonStyle.secondary, row=1)
    async def jump_to_songs(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.invoker:
            await interaction.response.send_message(
                "🚫 No puedes usar estos botones!",
                ephemeral=True
            )
            return
        self.current_section = 1
        await self.update_message(interaction)

    @discord.ui.button(emoji="🎤", label="Artists", style=discord.ButtonStyle.secondary, row=1)
    async def jump_to_artists(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.invoker:
            await interaction.response.send_message(
                "🚫 No puedes usar estos botones!",
                ephemeral=True
            )
            return
        self.current_section = 2
        await self.update_message(interaction)

    @discord.ui.button(emoji="📊", label="Stats", style=discord.ButtonStyle.secondary, row=1)
    async def jump_to_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.invoker:
            await interaction.response.send_message(
                "🚫 No puedes usar estos botones!",
                ephemeral=True
            )
            return
        self.current_section = 3
        await self.update_message(interaction)

    @discord.ui.button(emoji="🏆", label="Achievements", style=discord.ButtonStyle.secondary, row=1)
    async def jump_to_achievements(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.invoker:
            await interaction.response.send_message(
                "🚫 No puedes usar estos botones!",
                ephemeral=True
            )
            return
        self.current_section = 5
        await self.update_message(interaction)

    async def on_timeout(self):
        """Deshabilita todos los botones cuando expira el timeout"""
        for child in self.children:
            child.disabled = True
        try:
            if self.message:
                await self.message.edit(view=self)
        except Exception:
            pass
