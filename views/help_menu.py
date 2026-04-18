"""
Vista de menú de ayuda interactivo con selector de categorías
"""
import discord
from discord.ext import commands
from typing import Dict, List


class HelpMenuView(discord.ui.View):
    """Vista interactiva para el comando help con selector de categorías"""

    def __init__(self, ctx, bot: commands.Bot, timeout: float = 120):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.bot = bot
        self.message = None
        self.current_category = None

        # Nombres legibles para los Cogs
        self.cog_display_names = {
            "MusicCommands": ("🎵 Música", "Comandos de reproducción y control de música"),
            "WrappedCommands": ("🎁 Wrapped", "Estadísticas estilo Spotify Wrapped"),
        }

        # Construir categorías dinámicamente
        self.categories = self._build_categories()

        # Crear el selector
        self._create_select()

    def _build_categories(self) -> Dict[str, List[commands.Command]]:
        """Construye las categorías de comandos dinámicamente."""
        categories = {}

        for command in self.bot.commands:
            # Ignorar aliases
            if command.name != command.qualified_name:
                continue

            cog_name = command.cog.__class__.__name__ if command.cog else "Otros"

            if cog_name not in categories:
                categories[cog_name] = []
            categories[cog_name].append(command)

        # Ordenar comandos alfabéticamente dentro de cada categoría
        for cog_name in categories:
            categories[cog_name].sort(key=lambda c: c.name)

        return categories

    def _create_select(self):
        """Crea el menú desplegable con las categorías."""
        options = []

        for cog_name, cmds in self.categories.items():
            display_name, description = self.cog_display_names.get(
                cog_name,
                (f"📦 {cog_name}", f"Comandos de {cog_name}")
            )

            options.append(discord.SelectOption(
                label=display_name,
                description=f"{len(cmds)} comandos",
                value=cog_name
            ))

        # Agregar opción "Todos"
        total_commands = sum(len(cmds) for cmds in self.categories.values())
        options.insert(0, discord.SelectOption(
            label="📋 Resumen",
            description=f"Ver todas las categorías ({total_commands} comandos)",
            value="__all__"
        ))

        select = discord.ui.Select(
            placeholder="Selecciona una categoría...",
            options=options,
            custom_id="help_category_select"
        )
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        """Callback cuando se selecciona una categoría."""
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                "Solo quien ejecutó el comando puede usar este menú.",
                ephemeral=True
            )
            return

        selected = interaction.data["values"][0]
        self.current_category = selected

        if selected == "__all__":
            embed = self._create_summary_embed()
        else:
            embed = self._create_category_embed(selected)

        await interaction.response.edit_message(embed=embed, view=self)

    def _create_summary_embed(self) -> discord.Embed:
        """Crea el embed de resumen con todas las categorías."""
        embed = discord.Embed(
            title="📋 Comandos Disponibles",
            description="Selecciona una categoría del menú para ver los comandos detallados.\n\n"
                        "💡 **Tip:** Todos los comandos también están disponibles como **slash commands** (`/comando`).",
            color=discord.Color.blue()
        )

        for cog_name, cmds in self.categories.items():
            display_name, description = self.cog_display_names.get(
                cog_name,
                (f"📦 {cog_name}", f"Comandos de {cog_name}")
            )

            # Mostrar solo los nombres de los comandos
            cmd_names = ", ".join([f"`.{c.name}`" for c in cmds[:8]])
            if len(cmds) > 8:
                cmd_names += f" *y {len(cmds) - 8} más...*"

            embed.add_field(
                name=f"{display_name} ({len(cmds)})",
                value=cmd_names,
                inline=False
            )

        embed.set_footer(text="Prefijo: . | Slash: / | Usa el menú para ver detalles")
        return embed

    def _create_category_embed(self, cog_name: str) -> discord.Embed:
        """Crea el embed detallado para una categoría específica."""
        cmds = self.categories.get(cog_name, [])
        display_name, description = self.cog_display_names.get(
            cog_name,
            (f"📦 {cog_name}", f"Comandos de {cog_name}")
        )

        embed = discord.Embed(
            title=display_name,
            description=description,
            color=discord.Color.green()
        )

        for cmd in cmds:
            # Construir firma del comando con parámetros
            params = []
            for param_name, param in cmd.clean_params.items():
                if param.default == param.empty:
                    params.append(f"<{param_name}>")
                else:
                    params.append(f"[{param_name}]")

            signature = f".{cmd.name}"
            slash_signature = f"/{cmd.name}"
            if params:
                param_str = " " + " ".join(params)
                signature += param_str
                slash_signature += param_str

            # Descripción del comando
            help_text = cmd.help or "Sin descripción"

            embed.add_field(
                name=f"`{signature}` | `{slash_signature}`",
                value=help_text,
                inline=False
            )

        embed.set_footer(text=f"{len(cmds)} comandos en esta categoría")
        return embed

    async def on_timeout(self):
        """Deshabilita el menú cuando expira."""
        for item in self.children:
            item.disabled = True

        try:
            if self.message:
                await self.message.edit(view=self)
        except:
            pass


def create_help_initial_embed(bot: commands.Bot) -> discord.Embed:
    """Crea el embed inicial del menú de ayuda."""
    embed = discord.Embed(
        title="📋 Comandos Disponibles",
        description="Selecciona una categoría del menú para ver los comandos.",
        color=discord.Color.blue()
    )

    # Contar comandos por cog
    cog_counts = {}
    for command in bot.commands:
        if command.name != command.qualified_name:
            continue
        cog_name = command.cog.__class__.__name__ if command.cog else "Otros"
        cog_counts[cog_name] = cog_counts.get(cog_name, 0) + 1

    cog_display_names = {
        "MusicCommands": "🎵 Música",
        "WrappedCommands": "🎁 Wrapped",
    }

    summary_lines = []
    for cog_name, count in cog_counts.items():
        display_name = cog_display_names.get(cog_name, f"📦 {cog_name}")
        summary_lines.append(f"**{display_name}** - {count} comandos")

    embed.add_field(
        name="Categorías",
        value="\n".join(summary_lines),
        inline=False
    )

    total = sum(cog_counts.values())
    embed.set_footer(text=f"Total: {total} comandos | El menú expira en 2 minutos")
    return embed
