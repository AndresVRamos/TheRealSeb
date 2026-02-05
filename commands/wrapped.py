"""
Comandos Wrapped para Music Maniac bot
Proporciona estadísticas con un resumen estilo Wrapped para usuarios
"""
import discord
from discord.ext import commands
from datetime import datetime
from typing import Optional

from core.wrapped import generate_wrapped, create_wrapped_summary_embed
from core.database.queries import get_user_yearly_stats
from core.config import WRAPPED_MIN_YEAR, WRAPPED_TOP_ARTISTS_LIMIT


class WrappedCommands(commands.Cog):
    """Cog con comandos de estadísticas Wrapped"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="wrapped", help="Muestra tu resumen musical del año.")
    async def wrapped(self, ctx, member: Optional[discord.Member] = None, year: Optional[int] = None):
        """
        Genera un resumen estilo Wrapped para un usuario.

        Uso:
            .wrapped - Tu wrapped del año actual
            .wrapped @user - Wrapped de otro usuario
            .wrapped 2024 - Tu wrapped de un año específico
            .wrapped @user 2024 - Wrapped de alguien en un año específico
        """
        if member is None and year is None:
            member = ctx.author
            year = datetime.now().year
        elif member is not None and year is None:
            if isinstance(member, int) or (isinstance(member, str) and member.isdigit()):
                year = int(member) if isinstance(member, str) else member
                member = ctx.author
            else:
                year = datetime.now().year
        elif member is None:
            member = ctx.author

        current_year = datetime.now().year
        if year < WRAPPED_MIN_YEAR or year > current_year:
            await ctx.send(f"🚫 El año debe estar entre {WRAPPED_MIN_YEAR} y {current_year}.")
            return

        loading_msg = await ctx.send(f"🔄 **Generando tu Wrapped {year}...**")

        try:
            embed = await generate_wrapped(member, ctx.guild, year)

            if embed is None:
                if member == ctx.author:
                    await loading_msg.edit(
                        content=f"🚫 No tienes reproducciones registradas en {year}.\n"
                        f"¡Escucha música con el bot para generar tu Wrapped!"
                    )
                else:
                    await loading_msg.edit(
                        content=f"🚫 **{member.display_name}** no tiene reproducciones registradas en {year}."
                    )
                return

            await loading_msg.edit(content=None, embed=embed)

        except Exception as e:
            await loading_msg.edit(content=f"⚠️ Error al generar el Wrapped: {e}")

    @commands.command(name="wrappedsummary", aliases=["ws"], help="Muestra un resumen rápido de tu Wrapped.")
    async def wrapped_summary(self, ctx, member: Optional[discord.Member] = None, year: Optional[int] = None):
        """
        Genera un resumen rápido de Wrapped.

        Uso:
            .wrappedsummary - Resumen rápido del año actual
            .ws @user - Resumen rápido de otro usuario
        """
        if member is None:
            member = ctx.author
        if year is None:
            year = datetime.now().year

        current_year = datetime.now().year
        if year < WRAPPED_MIN_YEAR or year > current_year:
            await ctx.send(f"🚫 El año debe estar entre {WRAPPED_MIN_YEAR} y {current_year}.")
            return

        stats = get_user_yearly_stats(member.id, ctx.guild.id, year)

        if stats is None:
            if member == ctx.author:
                await ctx.send(f"🚫 No tienes reproducciones registradas en {year}.")
            else:
                await ctx.send(f"🚫 **{member.display_name}** no tiene reproducciones registradas en {year}.")
            return

        embed = create_wrapped_summary_embed(member, stats, ctx.guild)
        await ctx.send(embed=embed)

    @commands.command(name="topartists", help="Muestra tus artistas más escuchados del año.")
    async def top_artists(self, ctx, member: Optional[discord.Member] = None, year: Optional[int] = None):
        """
        Muestra los top artistas de un usuario en un año.

        Uso:
            .topartists - Tus top artistas de este año
            .topartists @user - Top artistas de otro usuario
            .topartists 2024 - Tus top artistas en 2024
        """
        if member is None:
            member = ctx.author
        if year is None:
            year = datetime.now().year

        if isinstance(member, int) or (hasattr(member, 'isdigit') and member.isdigit()):
            year = int(member)
            member = ctx.author

        stats = get_user_yearly_stats(member.id, ctx.guild.id, year)

        if stats is None or not stats.get('top_artists'):
            if member == ctx.author:
                await ctx.send(f"🚫 No tienes artistas registrados en {year}.")
            else:
                await ctx.send(f"🚫 **{member.display_name}** no tiene artistas registrados en {year}.")
            return

        embed = discord.Embed(
            title=f"🎤 Top Artistas {year}",
            description=f"**{member.display_name}** en **{ctx.guild.name}**",
            color=discord.Color.purple()
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        top_artists_text = []
        medals = ["🥇", "🥈", "🥉"] + [f"{i}." for i in range(4, WRAPPED_TOP_ARTISTS_LIMIT + 1)]
        for i, artist in enumerate(stats['top_artists'][:WRAPPED_TOP_ARTISTS_LIMIT]):
            from core.formatters import format_duration
            time_with_artist = format_duration(artist['total_time'])
            top_artists_text.append(
                f"{medals[i]} **{artist['name']}**\n"
                f"   └ {artist['play_count']} canciones ({time_with_artist})"
            )

        embed.add_field(
            name="Tus artistas favoritos",
            value="\n".join(top_artists_text),
            inline=False
        )

        embed.set_footer(text=f"Wrapped {year} | {ctx.guild.name}")
        await ctx.send(embed=embed)

    @commands.command(name="listeningtime", aliases=["lt"], help="Muestra cuánto tiempo has escuchado música.")
    async def listening_time(self, ctx, member: Optional[discord.Member] = None, year: Optional[int] = None):
        """
        Muestra el tiempo total de escucha de un usuario.

        Uso:
            .listeningtime - Tu tiempo de escucha este año
            .lt @user - Tiempo de escucha de otro usuario
        """
        if member is None:
            member = ctx.author
        if year is None:
            year = datetime.now().year

        stats = get_user_yearly_stats(member.id, ctx.guild.id, year)

        if stats is None:
            if member == ctx.author:
                await ctx.send(f"🚫 No tienes reproducciones registradas en {year}.")
            else:
                await ctx.send(f"🚫 **{member.display_name}** no tiene reproducciones registradas en {year}.")
            return

        from core.wrapped import format_time_detailed

        total_time = stats['total_time_seconds']
        hours = total_time // 3600
        minutes = (total_time % 3600) // 60

        embed = discord.Embed(
            title=f"⏱️ Tiempo de Escucha {year}",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        comparisons = []
        if hours >= 24:
            days = hours / 24
            comparisons.append(f"🌍 ¡Eso es **{days:.1f} días** de música continua!")
        if hours >= 2:
            movies = hours / 2
            comparisons.append(f"🎬 ¡Podrías ver **{int(movies)} películas** en ese tiempo!")
        if total_time >= 180:  # Al menos 3 minutos (1 canción)
            songs = total_time / 210  # Canción promedio ~3.5 min
            comparisons.append(f"🎵 ¡Aproximadamente **{int(songs)} canciones** promedio!")

        time_text = format_time_detailed(total_time)

        embed.add_field(
            name=f"**{member.display_name}**",
            value=f"🎧 **{time_text}**\n🔢 **{stats['total_plays']:,}** reproducciones",
            inline=False
        )

        if comparisons:
            embed.add_field(
                name="Datos curiosos",
                value="\n".join(comparisons),
                inline=False
            )

        embed.set_footer(text=f"{ctx.guild.name} | {year}")
        await ctx.send(embed=embed)

    @commands.command(name="streak", help="Muestra tu racha de días escuchando música.")
    async def streak(self, ctx, member: Optional[discord.Member] = None):
        """
        Muestra la racha de escucha de un usuario.

        Uso:
            .streak - Tu racha
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
            message = "Empieza tu racha hoy!"
        elif current_streak < 3:
            message = "Sigue construyendo tu racha!"
        elif current_streak < 7:
            message = "Bien! Casi una semana!"
        elif current_streak < 30:
            message = "WOW! Puedes llegar al mes!"
        else:
            message = "Más de un Mes! Verdaderamente eres el GOAT!"

        embed.add_field(
            name="💬",
            value=f"*{message}*",
            inline=False
        )

        embed.set_footer(text=ctx.guild.name)
        await ctx.send(embed=embed)


async def setup(bot):
    """Función de setup para cargar el Cog"""
    await bot.add_cog(WrappedCommands(bot))
