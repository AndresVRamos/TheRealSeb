"""
Comandos Wrapped para The Real Seb bot
Proporciona estadísticas con un resumen estilo Wrapped para usuarios
"""
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from typing import Optional

from core.database.queries import (
    get_user_yearly_stats,
    get_user_monthly_breakdown,
    get_user_records,
    get_user_rank_in_server,
    get_unique_songs_for_user,
    get_artist_discovery_timeline,
    get_favorite_changes,
    get_top_artist_growth,
    compare_users_wrapped
)
from core.config import WRAPPED_MIN_YEAR, WRAPPED_TOP_ARTISTS_LIMIT
from core.formatters import format_duration, create_comparison_bars
from core.decorators import command_category
from views.wrapped_navigator import WrappedNavigator


class WrappedCommands(commands.Cog):
    """Cog con comandos de estadísticas Wrapped"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="wrapped", help="Muestra tu resumen musical del año.")
    @command_category("wrapped")
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
            # Obtener estadísticas básicas
            stats = get_user_yearly_stats(member.id, ctx.guild.id, year)

            if stats is None:
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

            # Obtener datos extendidos
            extended_data = {
                'monthly_breakdown': get_user_monthly_breakdown(member.id, ctx.guild.id, year),
                'records': get_user_records(member.id, ctx.guild.id, year),
                'rank': get_user_rank_in_server(member.id, ctx.guild.id, year),
                'unique_songs': get_unique_songs_for_user(member.id, ctx.guild.id, year),
                'discovery_timeline': get_artist_discovery_timeline(member.id, ctx.guild.id, year),
                'favorite_changes': get_favorite_changes(member.id, ctx.guild.id, year),
                'top_artist_growth': get_top_artist_growth(member.id, ctx.guild.id, year, year - 1)
            }

            # Crear vista interactiva
            view = WrappedNavigator(ctx, member, stats, extended_data)
            first_embed = view.embeds[0]

            # Editar mensaje con el primer embed y la vista
            await loading_msg.edit(content=None, embed=first_embed, view=view)
            view.message = loading_msg

        except Exception as e:
            await loading_msg.edit(content=f"⚠️ Error al generar el Wrapped: {e}")

    @commands.command(name="wrappedbattle", aliases=["wb"], help="Compara tu Wrapped con otro usuario.")
    @command_category("wrapped")
    async def wrapped_battle(self, ctx, member: discord.Member, year: Optional[int] = None):
        """
        Batalla de Wrapped 1v1 con otro usuario.

        Uso:
            .wrappedbattle @user - Batalla del año actual
            .wb @user 2024 - Batalla de un año específico
        """
        if year is None:
            year = datetime.now().year

        current_year = datetime.now().year
        if year < WRAPPED_MIN_YEAR or year > current_year:
            await ctx.send(f"🚫 El año debe estar entre {WRAPPED_MIN_YEAR} y {current_year}.")
            return

        if member == ctx.author:
            await ctx.send("🚫 No puedes batallar contra ti mismo!")
            return

        loading_msg = await ctx.send(f"⚔️ **Preparando batalla Wrapped {year}...**")

        try:
            # Obtener comparación entre usuarios
            comparison = compare_users_wrapped(ctx.author.id, member.id, ctx.guild.id, year)

            if comparison is None:
                await loading_msg.edit(
                    content=f"🚫 No hay suficientes datos para comparar en {year}.\n"
                    f"Ambos usuarios deben tener reproducciones registradas."
                )
                return

            # Crear embed de batalla
            embed = discord.Embed(
                title=f"⚔️ Wrapped Battle {year}",
                description=f"**{ctx.author.display_name}** vs **{member.display_name}**",
                color=discord.Color.gold()
            )
            embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)

            # Categoría 1: Tiempo Total
            time_comparison = create_comparison_bars(
                comparison['user1']['total_time_seconds'],
                comparison['user2']['total_time_seconds'],
                ctx.author.display_name,
                member.display_name,
                "⏱️ Tiempo Total",
                max_width=15,
                value_type="hours"
            )
            embed.add_field(name="\u200b", value=time_comparison, inline=False)

            # Categoría 2: Variedad (canciones únicas)
            variety_comparison = create_comparison_bars(
                comparison['user1']['unique_tracks'],
                comparison['user2']['unique_tracks'],
                ctx.author.display_name,
                member.display_name,
                "🎵 Variedad Musical",
                max_width=15,
                value_type="count"
            )
            embed.add_field(name="\u200b", value=variety_comparison, inline=False)

            # Categoría 3: Exploración (artistas únicos)
            exploration_comparison = create_comparison_bars(
                comparison['user1']['unique_artists'],
                comparison['user2']['unique_artists'],
                ctx.author.display_name,
                member.display_name,
                "🔭 Exploración",
                max_width=15,
                value_type="count"
            )
            embed.add_field(name="\u200b", value=exploration_comparison, inline=False)

            # Categoría 4: Lealtad (plays del top artista)
            loyalty_comparison = create_comparison_bars(
                comparison['user1']['top_artist_plays'],
                comparison['user2']['top_artist_plays'],
                ctx.author.display_name,
                member.display_name,
                "💎 Lealtad",
                max_width=15,
                value_type="count"
            )
            embed.add_field(name="\u200b", value=loyalty_comparison, inline=False)

            # Categoría 5: Racha más larga
            streak_comparison = create_comparison_bars(
                comparison['user1']['longest_streak'],
                comparison['user2']['longest_streak'],
                ctx.author.display_name,
                member.display_name,
                "🔥 Racha Máxima",
                max_width=15,
                value_type="days"
            )
            embed.add_field(name="\u200b", value=streak_comparison, inline=False)

            # Determinar ganador global
            user1_wins = 0
            user2_wins = 0

            if comparison['user1']['total_time_seconds'] > comparison['user2']['total_time_seconds']:
                user1_wins += 1
            elif comparison['user2']['total_time_seconds'] > comparison['user1']['total_time_seconds']:
                user2_wins += 1

            if comparison['user1']['unique_tracks'] > comparison['user2']['unique_tracks']:
                user1_wins += 1
            elif comparison['user2']['unique_tracks'] > comparison['user1']['unique_tracks']:
                user2_wins += 1

            if comparison['user1']['unique_artists'] > comparison['user2']['unique_artists']:
                user1_wins += 1
            elif comparison['user2']['unique_artists'] > comparison['user1']['unique_artists']:
                user2_wins += 1

            if comparison['user1']['top_artist_plays'] > comparison['user2']['top_artist_plays']:
                user1_wins += 1
            elif comparison['user2']['top_artist_plays'] > comparison['user1']['top_artist_plays']:
                user2_wins += 1

            if comparison['user1']['longest_streak'] > comparison['user2']['longest_streak']:
                user1_wins += 1
            elif comparison['user2']['longest_streak'] > comparison['user1']['longest_streak']:
                user2_wins += 1

            # Resultado final
            if user1_wins > user2_wins:
                winner_text = f"🏆 **{ctx.author.display_name}** gana la batalla! ({user1_wins}-{user2_wins})"
            elif user2_wins > user1_wins:
                winner_text = f"🏆 **{member.display_name}** gana la batalla! ({user2_wins}-{user1_wins})"
            else:
                winner_text = f"🤝 ¡Empate perfecto! ({user1_wins}-{user2_wins})"

            embed.add_field(
                name="📊 Resultado Final",
                value=winner_text,
                inline=False
            )

            embed.set_footer(text=f"Wrapped Battle {year} | {ctx.guild.name}")

            await loading_msg.edit(content=None, embed=embed)

        except Exception as e:
            await loading_msg.edit(content=f"⚠️ Error al generar la batalla: {e}")

    # ==========================================
    # SLASH COMMANDS
    # ==========================================

    @app_commands.command(name="wrapped", description="Muestra tu resumen musical del año")
    @app_commands.describe(
        usuario="Usuario del que ver el Wrapped (opcional)",
        year="Año del Wrapped (opcional, por defecto el actual)"
    )
    async def wrapped_slash(
        self,
        interaction: discord.Interaction,
        usuario: Optional[discord.Member] = None,
        year: Optional[int] = None
    ):
        await interaction.response.defer()

        member = usuario if usuario else interaction.user
        if year is None:
            year = datetime.now().year

        current_year = datetime.now().year
        if year < WRAPPED_MIN_YEAR or year > current_year:
            await interaction.followup.send(f"🚫 El año debe estar entre {WRAPPED_MIN_YEAR} y {current_year}.")
            return

        try:
            # Obtener estadísticas básicas
            stats = get_user_yearly_stats(member.id, interaction.guild.id, year)

            if stats is None:
                if member == interaction.user:
                    await interaction.followup.send(
                        f"🚫 No tienes reproducciones registradas en {year}.\n"
                        f"¡Escucha música con el bot para generar tu Wrapped!"
                    )
                else:
                    await interaction.followup.send(
                        f"🚫 **{member.display_name}** no tiene reproducciones registradas en {year}."
                    )
                return

            # Obtener datos extendidos
            extended_data = {
                'monthly_breakdown': get_user_monthly_breakdown(member.id, interaction.guild.id, year),
                'records': get_user_records(member.id, interaction.guild.id, year),
                'rank': get_user_rank_in_server(member.id, interaction.guild.id, year),
                'unique_songs': get_unique_songs_for_user(member.id, interaction.guild.id, year),
                'discovery_timeline': get_artist_discovery_timeline(member.id, interaction.guild.id, year),
                'favorite_changes': get_favorite_changes(member.id, interaction.guild.id, year),
                'top_artist_growth': get_top_artist_growth(member.id, interaction.guild.id, year, year - 1)
            }

            # Crear vista interactiva (pasar interaction en lugar de ctx)
            view = WrappedNavigator(interaction, member, stats, extended_data)
            first_embed = view.embeds[0]

            # Enviar mensaje con el primer embed y la vista
            msg = await interaction.followup.send(embed=first_embed, view=view)
            view.message = msg

        except Exception as e:
            await interaction.followup.send(f"⚠️ Error al generar el Wrapped: {e}")

    @app_commands.command(name="wrappedbattle", description="Compara tu Wrapped con otro usuario")
    @app_commands.describe(
        usuario="Usuario con el que competir",
        year="Año (opcional, por defecto el actual)"
    )
    async def wrappedbattle_slash(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
        year: Optional[int] = None
    ):
        if year is None:
            year = datetime.now().year

        current_year = datetime.now().year
        if year < WRAPPED_MIN_YEAR or year > current_year:
            await interaction.response.send_message(
                f"🚫 El año debe estar entre {WRAPPED_MIN_YEAR} y {current_year}.",
                ephemeral=True
            )
            return

        if usuario == interaction.user:
            await interaction.response.send_message(
                "🚫 No puedes batallar contra ti mismo!",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        try:
            # Obtener comparación entre usuarios
            comparison = compare_users_wrapped(interaction.user.id, usuario.id, interaction.guild_id, year)

            if comparison is None:
                await interaction.followup.send(
                    f"🚫 No hay suficientes datos para comparar en {year}.\n"
                    f"Ambos usuarios deben tener reproducciones registradas."
                )
                return

            # Crear embed de batalla
            embed = discord.Embed(
                title=f"⚔️ Wrapped Battle {year}",
                description=f"**{interaction.user.display_name}** vs **{usuario.display_name}**",
                color=discord.Color.gold()
            )
            embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)

            # Categoría 1: Tiempo Total
            time_comparison = create_comparison_bars(
                comparison['user1']['total_time_seconds'],
                comparison['user2']['total_time_seconds'],
                interaction.user.display_name,
                usuario.display_name,
                "⏱️ Tiempo Total",
                max_width=15,
                value_type="hours"
            )
            embed.add_field(name="\u200b", value=time_comparison, inline=False)

            # Categoría 2: Variedad (canciones únicas)
            variety_comparison = create_comparison_bars(
                comparison['user1']['unique_tracks'],
                comparison['user2']['unique_tracks'],
                interaction.user.display_name,
                usuario.display_name,
                "🎵 Variedad Musical",
                max_width=15,
                value_type="count"
            )
            embed.add_field(name="\u200b", value=variety_comparison, inline=False)

            # Categoría 3: Exploración (artistas únicos)
            exploration_comparison = create_comparison_bars(
                comparison['user1']['unique_artists'],
                comparison['user2']['unique_artists'],
                interaction.user.display_name,
                usuario.display_name,
                "🔭 Exploración",
                max_width=15,
                value_type="count"
            )
            embed.add_field(name="\u200b", value=exploration_comparison, inline=False)

            # Categoría 4: Lealtad (plays del top artista)
            loyalty_comparison = create_comparison_bars(
                comparison['user1']['top_artist_plays'],
                comparison['user2']['top_artist_plays'],
                interaction.user.display_name,
                usuario.display_name,
                "💎 Lealtad",
                max_width=15,
                value_type="count"
            )
            embed.add_field(name="\u200b", value=loyalty_comparison, inline=False)

            # Categoría 5: Racha más larga
            streak_comparison = create_comparison_bars(
                comparison['user1']['longest_streak'],
                comparison['user2']['longest_streak'],
                interaction.user.display_name,
                usuario.display_name,
                "🔥 Racha Máxima",
                max_width=15,
                value_type="days"
            )
            embed.add_field(name="\u200b", value=streak_comparison, inline=False)

            # Determinar ganador global
            user1_wins = 0
            user2_wins = 0

            if comparison['user1']['total_time_seconds'] > comparison['user2']['total_time_seconds']:
                user1_wins += 1
            elif comparison['user2']['total_time_seconds'] > comparison['user1']['total_time_seconds']:
                user2_wins += 1

            if comparison['user1']['unique_tracks'] > comparison['user2']['unique_tracks']:
                user1_wins += 1
            elif comparison['user2']['unique_tracks'] > comparison['user1']['unique_tracks']:
                user2_wins += 1

            if comparison['user1']['unique_artists'] > comparison['user2']['unique_artists']:
                user1_wins += 1
            elif comparison['user2']['unique_artists'] > comparison['user1']['unique_artists']:
                user2_wins += 1

            if comparison['user1']['top_artist_plays'] > comparison['user2']['top_artist_plays']:
                user1_wins += 1
            elif comparison['user2']['top_artist_plays'] > comparison['user1']['top_artist_plays']:
                user2_wins += 1

            if comparison['user1']['longest_streak'] > comparison['user2']['longest_streak']:
                user1_wins += 1
            elif comparison['user2']['longest_streak'] > comparison['user1']['longest_streak']:
                user2_wins += 1

            # Resultado final
            if user1_wins > user2_wins:
                winner_text = f"🏆 **{interaction.user.display_name}** gana la batalla! ({user1_wins}-{user2_wins})"
            elif user2_wins > user1_wins:
                winner_text = f"🏆 **{usuario.display_name}** gana la batalla! ({user2_wins}-{user1_wins})"
            else:
                winner_text = f"🤝 ¡Empate perfecto! ({user1_wins}-{user2_wins})"

            embed.add_field(
                name="📊 Resultado Final",
                value=winner_text,
                inline=False
            )

            embed.set_footer(text=f"Wrapped Battle {year} | {interaction.guild.name}")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"⚠️ Error al generar la batalla: {e}")


async def setup(bot):
    """Función de setup para cargar el Cog"""
    await bot.add_cog(WrappedCommands(bot))
