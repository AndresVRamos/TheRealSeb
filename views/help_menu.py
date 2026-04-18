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

        # Nombres legibles para las categorías funcionales
        self.category_display_names = {
            "playback": ("🎵 Reproducción", "Comandos para reproducir música"),
            "control": ("⏯️ Control", "Controles de reproducción"),
            "queue": ("📋 Cola", "Gestión de la cola de reproducción"),
            "config": ("⚙️ Configuración", "Ajustes del bot"),
            "stats": ("📊 Estadísticas", "Estadísticas de escucha"),
            "info": ("ℹ️ Información", "Información y ayuda"),
            "wrapped": ("🎁 Wrapped", "Estadísticas estilo Spotify Wrapped"),
        }

        # Orden de las categorías en el menú
        self.category_order = ["playback", "control", "queue", "config", "stats", "info", "wrapped"]

        # Construir categorías dinámicamente
        self.categories = self._build_categories()

        # Crear el selector
        self._create_select()

    def _build_categories(self) -> Dict[str, List[commands.Command]]:
        """Construye las categorías de comandos basadas en función."""
        categories = {}

        for command in self.bot.commands:
            # Ignorar aliases y comandos ocultos
            if command.name != command.qualified_name:
                continue
            if command.hidden:
                continue

            # Obtener categoría del atributo del comando (definido por @command_category)
            category = getattr(command.callback, 'category', None)
            if category is None:
                continue  # Ignorar comandos sin categoría asignada

            if category not in categories:
                categories[category] = []
            categories[category].append(command)

        # Ordenar comandos alfabéticamente dentro de cada categoría
        for category in categories:
            categories[category].sort(key=lambda c: c.name)

        return categories

    def _create_select(self):
        """Crea el menú desplegable con las categorías."""
        options = []

        # Seguir el orden definido en category_order
        for category in self.category_order:
            if category not in self.categories:
                continue  # Saltar categorías vacías (ej: wrapped si no está habilitado)

            cmds = self.categories[category]
            display_name, description = self.category_display_names.get(
                category,
                (f"📦 {category}", f"Comandos de {category}")
            )

            options.append(discord.SelectOption(
                label=display_name,
                description=f"{len(cmds)} comandos",
                value=category
            ))

        # Agregar opción "Resumen" al inicio
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

        # Seguir el orden definido
        for category in self.category_order:
            if category not in self.categories:
                continue

            cmds = self.categories[category]
            display_name, description = self.category_display_names.get(
                category,
                (f"📦 {category}", f"Comandos de {category}")
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

    def _create_category_embed(self, category: str) -> discord.Embed:
        """Crea el embed detallado para una categoría específica."""
        cmds = self.categories.get(category, [])
        display_name, description = self.category_display_names.get(
            category,
            (f"📦 {category}", f"Comandos de {category}")
        )

        embed = discord.Embed(
            title=display_name,
            description=description,
            color=discord.Color.green()
        )

        # Discord limita a 25 campos por embed
        # Si hay más de 24 comandos, agrupar en descripción
        if len(cmds) > 24:
            cmd_lines = []
            for cmd in cmds:
                params = []
                for param_name, param in cmd.clean_params.items():
                    if param.default == param.empty:
                        params.append(f"<{param_name}>")
                    else:
                        params.append(f"[{param_name}]")

                signature = f".{cmd.name}"
                if params:
                    signature += " " + " ".join(params)

                help_text = cmd.help or "Sin descripción"
                cmd_lines.append(f"`{signature}` - {help_text}")

            # Dividir en chunks para no exceder límite de caracteres
            chunk_size = 13
            for i in range(0, len(cmd_lines), chunk_size):
                chunk = cmd_lines[i:i + chunk_size]
                field_name = "Comandos" if i == 0 else "​"  # Zero-width space para campos adicionales
                embed.add_field(
                    name=field_name,
                    value="\n".join(chunk),
                    inline=False
                )
        else:
            for cmd in cmds:
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

                help_text = cmd.help or "Sin descripción"

                embed.add_field(
                    name=f"`{signature}` | `{slash_signature}`",
                    value=help_text,
                    inline=False
                )

        embed.set_footer(text=f"{len(cmds)} comandos en esta categoría | Prefijo: . | Slash: /")
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

    category_display_names = {
        "playback": "🎵 Reproducción",
        "control": "⏯️ Control",
        "queue": "📋 Cola",
        "config": "⚙️ Configuración",
        "stats": "📊 Estadísticas",
        "info": "ℹ️ Información",
        "wrapped": "🎁 Wrapped",
    }

    category_order = ["playback", "control", "queue", "config", "stats", "info", "wrapped"]

    # Contar comandos por categoría funcional (ignorar ocultos)
    category_counts = {}
    for command in bot.commands:
        if command.name != command.qualified_name:
            continue
        if command.hidden:
            continue
        # Leer categoría del atributo del comando
        category = getattr(command.callback, 'category', None)
        if category:
            category_counts[category] = category_counts.get(category, 0) + 1

    summary_lines = []
    for category in category_order:
        if category in category_counts:
            display_name = category_display_names.get(category, f"📦 {category}")
            summary_lines.append(f"**{display_name}** - {category_counts[category]} comandos")

    embed.add_field(
        name="Categorías",
        value="\n".join(summary_lines),
        inline=False
    )

    total = sum(category_counts.values())
    embed.set_footer(text=f"Total: {total} comandos | El menú expira en 2 minutos")
    return embed
