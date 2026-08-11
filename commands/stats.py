"""
Comandos de estadísticas para The Real Seb bot
Comandos básicos de stats que funcionan independientemente de Wrapped
"""
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from typing import Optional

from core.stats_handler import (
    get_user_stats,
    get_user_top_songs,
    get_server_top_songs,
    get_server_top_users,
    get_server_stats,
    get_user_history,
    get_user_yearly_stats
)
from core.config import (
    USER_TOP_SONGS_LIMIT,
    TOP_SONGS_LIMIT,
    TOP_USERS_LIMIT,
    HISTORY_LIMIT
)
from core.formatters import format_duration
from core.decorators import command_category
from commands.music import UnifiedContext


class StatsCommands(commands.Cog):
    """Cog con comandos de estadísticas básicas"""

    def __init__(self, bot):
        self.bot = bot

    # === COMANDOS PREFIX ===

    @commands.command(name="mystats", help="Muestra tus estadísticas de reproducciones en este servidor.")
    @command_category("stats")
    async def mystats(self, ctx):
        await self.show_user_stats(UnifiedContext(ctx), ctx.author, is_self=True)

    @commands.command(name="stats", help="Muestra las estadísticas de un usuario específico.")
    @command_category("stats")
    async def stats(self, ctx, member: discord.Member = None):
        target = member if member else ctx.author
        is_self = member is None
        await self.show_user_stats(UnifiedContext(ctx), target, is_self=is_self)

    @commands.command(name="topsongs", help="Muestra las canciones más reproducidas en este servidor.")
    @command_category("stats")
    async def topsongs(self, ctx):
        await self.show_top_songs(UnifiedContext(ctx))

    @commands.command(name="topusers", help="Muestra los usuarios más activos del servidor.")
    @command_category("stats")
    async def topusers(self, ctx):
        await self.show_top_users(UnifiedContext(ctx))

    @commands.command(name="serverstats", help="Muestra las estadísticas generales del servidor.")
    @command_category("stats")
    async def serverstats(self, ctx):
        await self.show_server_stats(UnifiedContext(ctx))

    @commands.command(name="history", help="Muestra tu historial de reproducciones recientes.")
    @command_category("stats")
    async def history(self, ctx, member: discord.Member = None):
        await self.show_history(UnifiedContext(ctx), member)

    @commands.command(name="streak", help="Muestra tu racha de días escuchando música.")
    @command_category("stats")
    async def streak(self, ctx, member: Optional[discord.Member] = None):
        """
        Muestra la racha de escucha de un usuario.

        Uso:
            .streak - Tu racha actual
            .streak @user - Racha de otro usuario
        """
        if member is None:
            member = ctx.author

        year = datetime.now().year
        stats = get_user_yearly_stats(member.id, ctx.guild.id, year)

        if stats is None:
            if member == ctx.author:
                await ctx.send("🚫 No tienes reproducciones registradas.")
            else:
                await ctx.send(f"🚫 **{member.display_name}** no tiene reproducciones registradas.")
            return

        embed = discord.Embed(
            title="🔥 Racha de Escucha",
            color=discord.Color.orange()
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        current_streak = stats.get('current_streak', 0)
        longest_streak = stats.get('longest_streak', 0)

        streak_emoji = "🔥"
        if current_streak >= 30:
            streak_emoji = "🌟"
        elif current_streak >= 7:
            streak_emoji = "💫"
        elif current_streak >= 3:
            streak_emoji = "✨"

        embed.add_field(
            name=f"**{member.display_name}**",
            value=f"{streak_emoji} **Racha actual:** {current_streak} días\n"
                  f"🏆 **Racha más larga:** {longest_streak} días",
            inline=False
        )

        if current_streak == 0:
            message = "¡Empieza tu racha hoy!"
        elif current_streak < 3:
            message = "¡Sigue construyendo tu racha!"
        elif current_streak < 7:
            message = "¡Bien! Casi una semana!"
        elif current_streak < 30:
            message = "¡WOW! ¡Puedes llegar al mes!"
        else:
            message = "¡Más de un mes! ¡Verdaderamente eres el GOAT!"

        embed.add_field(
            name="💬 Mensaje",
            value=message,
            inline=False
        )

        embed.set_footer(text=f"Servidor: {ctx.guild.name} • Año {year}")
        await ctx.send(embed=embed)

    # === COMANDOS SLASH ===

    @app_commands.command(name="mystats", description="Muestra tus estadísticas de reproducciones")
    async def mystats_slash(self, interaction: discord.Interaction):
        ctx = UnifiedContext(interaction)
        await self.show_user_stats(ctx, ctx.author, is_self=True)

    @app_commands.command(name="stats", description="Muestra las estadísticas de un usuario")
    @app_commands.describe(usuario="Usuario del que ver las estadísticas (opcional)")
    async def stats_slash(self, interaction: discord.Interaction, usuario: discord.Member = None):
        ctx = UnifiedContext(interaction)
        target = usuario if usuario else ctx.author
        await self.show_user_stats(ctx, target, is_self=(usuario is None))

    @app_commands.command(name="history", description="Muestra el historial de reproducciones recientes")
    @app_commands.describe(usuario="Usuario del que ver el historial (opcional)")
    async def history_slash(self, interaction: discord.Interaction, usuario: discord.Member = None):
        await self.show_history(UnifiedContext(interaction), usuario)

    @app_commands.command(name="topsongs", description="Muestra las canciones más reproducidas del servidor")
    async def topsongs_slash(self, interaction: discord.Interaction):
        await self.show_top_songs(UnifiedContext(interaction))

    @app_commands.command(name="topusers", description="Muestra los usuarios más activos del servidor")
    async def topusers_slash(self, interaction: discord.Interaction):
        await self.show_top_users(UnifiedContext(interaction))

    @app_commands.command(name="serverstats", description="Muestra las estadísticas generales del servidor")
    async def serverstats_slash(self, interaction: discord.Interaction):
        await self.show_server_stats(UnifiedContext(interaction))

    @app_commands.command(name="streak", description="Muestra tu racha de días escuchando música")
    @app_commands.describe(usuario="Usuario del que ver la racha (opcional)")
    async def streak_slash(
        self,
        interaction: discord.Interaction,
        usuario: Optional[discord.Member] = None
    ):
        member = usuario if usuario else interaction.user
        year = datetime.now().year
        stats = get_user_yearly_stats(member.id, interaction.guild.id, year)

        if stats is None:
            if member == interaction.user:
                await interaction.response.send_message("🚫 No tienes reproducciones registradas.")
            else:
                await interaction.response.send_message(f"🚫 **{member.display_name}** no tiene reproducciones registradas.")
            return

        embed = discord.Embed(
            title="🔥 Racha de Escucha",
            color=discord.Color.orange()
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        current_streak = stats.get('current_streak', 0)
        longest_streak = stats.get('longest_streak', 0)

        streak_emoji = "🔥"
        if current_streak >= 30:
            streak_emoji = "🌟"
        elif current_streak >= 7:
            streak_emoji = "💫"
        elif current_streak >= 3:
            streak_emoji = "✨"

        embed.add_field(
            name=f"**{member.display_name}**",
            value=f"{streak_emoji} **Racha actual:** {current_streak} días\n"
                  f"🏆 **Racha más larga:** {longest_streak} días",
            inline=False
        )

        if current_streak == 0:
            message = "¡Empieza tu racha hoy!"
        elif current_streak < 3:
            message = "¡Sigue construyendo tu racha!"
        elif current_streak < 7:
            message = "¡Bien! Casi una semana!"
        elif current_streak < 30:
            message = "¡WOW! ¡Puedes llegar al mes!"
        else:
            message = "¡Más de un mes! ¡Verdaderamente eres el GOAT!"

        embed.add_field(
            name="💬 Mensaje",
            value=message,
            inline=False
        )

        embed.set_footer(text=f"Servidor: {interaction.guild.name} • Año {year}")
        await interaction.response.send_message(embed=embed)

    # === MÉTODOS DE IMPLEMENTACIÓN ===

    async def show_user_stats(self, ctx: UnifiedContext, member: discord.Member, is_self: bool = False):
        """Muestra estadísticas de un usuario (compartido entre mystats/stats)"""
        guild_id = ctx.guild.id
        user_id = member.id

        stats = get_user_stats(user_id, guild_id)

        if stats['total_listened'] == 0:
            if is_self:
                await ctx.send("🚫 **No tienes reproducciones registradas en este servidor.**")
            else:
                await ctx.send(f"🚫 **{member.display_name} no tiene reproducciones registradas en este servidor.**")
            return

        top_songs = get_user_top_songs(user_id, guild_id, limit=USER_TOP_SONGS_LIMIT)

        embed = discord.Embed(
            title=f"📊 Estadísticas de {member.display_name}",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        embed.add_field(name="🎵 Canciones pedidas", value=str(stats['total_requested']), inline=True)
        embed.add_field(name="🎧 Canciones escuchadas", value=str(stats['total_listened']), inline=True)
        embed.add_field(name="⏱️ Tiempo total escuchado", value=format_duration(stats['total_time']), inline=True)

        if stats['first_play']:
            embed.add_field(name="📅 Primera reproducción", value=stats['first_play'][:10], inline=True)

        if top_songs:
            top_label = "🏆 Tus Top 5 canciones pedidas" if is_self else "🏆 Top 5 canciones pedidas"
            top_songs_text = "\n".join([
                f"**{i+1}.** {song[0]} ({song[2]} reproducciones)"
                for i, song in enumerate(top_songs)
            ])
            embed.add_field(name=top_label, value=top_songs_text, inline=False)

        embed.set_footer(text=f"Servidor: {ctx.guild.name}")
        await ctx.send(embed=embed)

    async def show_top_songs(self, ctx: UnifiedContext):
        """Muestra las canciones más reproducidas del servidor"""
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
            medal = "🥇 " if i == 0 else "🥈 " if i == 1 else "🥉 " if i == 2 else ""
            artist_text = f" - *{song[1]}*" if song[1] else ""
            songs_text.append(f"{medal}**{i+1}.** {song[0]}{artist_text} ({song[2]} reproducciones)")

        embed.description = "\n".join(songs_text)
        embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
        await ctx.send(embed=embed)

    async def show_top_users(self, ctx: UnifiedContext):
        """Muestra los usuarios más activos del servidor"""
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
            medal = "🥇 " if i == 0 else "🥈 " if i == 1 else "🥉 " if i == 2 else ""
            time_str = format_duration(total_time)
            users_text.append(f"{medal}**{i+1}.** {user_name} - {play_count} requests ({time_str})")

        embed.description = "\n".join(users_text)
        embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
        await ctx.send(embed=embed)

    async def show_server_stats(self, ctx: UnifiedContext):
        """Muestra estadísticas generales del servidor"""
        guild_id = ctx.guild.id

        stats = get_server_stats(guild_id)

        if stats['total_plays'] == 0:
            await ctx.send("🚫 **No hay reproducciones registradas en este servidor.**")
            return

        top_songs = get_server_top_songs(guild_id, limit=5)
        top_users = get_server_top_users(guild_id, limit=5)

        embed = discord.Embed(
            title=f"📊 Estadísticas del Servidor",
            color=discord.Color.blurple()
        )
        embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)

        # Stats generales
        embed.add_field(name="🎵 Total reproducciones", value=str(stats['total_plays']), inline=True)
        embed.add_field(name="⏱️ Tiempo total", value=format_duration(stats['total_time']), inline=True)
        embed.add_field(name="💿 Canciones únicas", value=str(stats['unique_tracks']), inline=True)
        embed.add_field(name="🎤 Artistas únicos", value=str(stats['unique_artists']), inline=True)

        if stats['first_play']:
            embed.add_field(name="📅 Primera reproducción", value=stats['first_play'][:10], inline=True)

        # Top usuario
        if top_users:
            _, user_name, play_count, _ = top_users[0]
            embed.add_field(
                name="👑 Usuario más activo",
                value=f"**{user_name}** ({play_count} requests)",
                inline=True
            )

        # Top 5 canciones
        if top_songs:
            songs_text = []
            for i, song in enumerate(top_songs):
                medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"**{i+1}.**"
                artist_text = f" - *{song[1]}*" if song[1] else ""
                songs_text.append(f"{medal} {song[0]}{artist_text} ({song[2]})")
            embed.add_field(name="🏆 Top 5 Canciones", value="\n".join(songs_text), inline=False)

        # Top 5 usuarios
        if top_users:
            users_text = []
            for i, user_data in enumerate(top_users):
                _, user_name, play_count, total_time = user_data
                medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"**{i+1}.**"
                users_text.append(f"{medal} {user_name} - {play_count} ({format_duration(total_time)})")
            embed.add_field(name="👥 Top 5 Usuarios", value="\n".join(users_text), inline=False)

        embed.set_footer(text=ctx.guild.name)
        await ctx.send(embed=embed)

    async def show_history(self, ctx: UnifiedContext, member: discord.Member = None):
        """Muestra el historial de reproducciones recientes"""
        guild_id = ctx.guild.id
        target = member if member else ctx.author
        is_self = member is None

        history = get_user_history(target.id, guild_id, limit=HISTORY_LIMIT)

        if not history:
            if is_self:
                await ctx.send("🚫 **No tienes historial de reproducciones en este servidor.**")
            else:
                await ctx.send(f"🚫 **{target.display_name} no tiene historial de reproducciones en este servidor.**")
            return

        embed = discord.Embed(
            title=f"📜 Historial de {target.display_name}",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=target.display_avatar.url)

        history_text = []
        for i, (song_title, artist, played_at) in enumerate(history):
            date_str = played_at[:16].replace("T", " ") if "T" in played_at else played_at[:16]
            song_info = f"**{i+1}.** {song_title}"
            if artist:
                song_info += f" - *{artist}*"
            song_info += f"\n   └ {date_str}"
            history_text.append(song_info)

        embed.description = "\n".join(history_text)
        embed.set_footer(text=f"Últimas {HISTORY_LIMIT} reproducciones en {ctx.guild.name}")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(StatsCommands(bot))
