"""
Generador de estadísticas Wrapped para The Real Seb bot
Genera embeds estilo Spotify Wrapped con estadísticas anuales
"""
import discord
from datetime import datetime
from typing import Optional, List, Dict, Any

from core.database.queries import (
    get_user_yearly_stats,
    get_user_listening_hours,
    get_user_listening_days
)
from core.formatters import format_duration
from core.config import WRAPPED_TOP_TRACKS_LIMIT, WRAPPED_TOP_ARTISTS_LIMIT, SPOTIFY_GREEN_RGB


# Nombres de días en español
DAY_NAMES = {
    0: "Domingo",
    1: "Lunes",
    2: "Martes",
    3: "Miércoles",
    4: "Jueves",
    5: "Viernes",
    6: "Sábado"
}

# Nombres de períodos del día
TIME_PERIODS = {
    'morning': (5, 11, "Mañana"),
    'afternoon': (12, 17, "Tarde"),
    'evening': (18, 21, "Noche"),
    'night': (22, 4, "Madrugada")
}

# Descripciones de personalidades
PERSONALITY_DESCRIPTIONS = {
    "Explorer": "Siempre buscando nuevos sonidos y artistas.",
    "Loyalist": "Tienes tus favoritos y les eres fiel.",
    "Devoted Fan": "Un súper fan de tus artistas favoritos.",
    "Night Owl": "La noche es tu momento para la música.",
    "Early Bird": "Empiezas el día con buena música.",
    "Specialist": "Te enfocas en unos pocos artistas selectos.",
    "Music Enthusiast": "La música es una parte importante de tu vida.",
    "Casual Listener": "Disfrutas la música a tu propio ritmo.",
    "Newcomer": "¡Apenas estás comenzando tu viaje musical!"
}

# Emojis de personalidades
PERSONALITY_EMOJIS = {
    "Explorer": "🔭",
    "Loyalist": "💎",
    "Devoted Fan": "🌟",
    "Night Owl": "🦉",
    "Early Bird": "🐦",
    "Specialist": "🎯",
    "Music Enthusiast": "🎶",
    "Casual Listener": "😌",
    "Newcomer": "🌱"
}


def get_time_period(hour: int) -> str:
    """Obtiene el nombre del período del día para una hora dada."""
    if 5 <= hour <= 11:
        return "Mañana"
    elif 12 <= hour <= 17:
        return "Tarde"
    elif 18 <= hour <= 21:
        return "Noche"
    else:
        return "Madrugada"


def get_time_period_emoji(hour: int) -> str:
    """Obtiene el emoji correspondiente al período del día."""
    if 5 <= hour <= 11:
        return "🌅"
    elif 12 <= hour <= 17:
        return "☀️"
    elif 18 <= hour <= 21:
        return "🌆"
    else:
        return "🌙"


def format_time_detailed(total_seconds: int) -> str:
    """Formatea el tiempo en formato detallado para Wrapped."""
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60

    if hours > 0:
        return f"{hours:,} horas y {minutes} minutos"
    else:
        return f"{minutes} minutos"


def create_wrapped_embed(user: discord.Member, stats: Dict[str, Any],
                         guild: discord.Guild) -> discord.Embed:
    """
    Crea un embed completo estilo Wrapped para un usuario.

    Args:
        user: Miembro de Discord para crear el wrapped
        stats: Diccionario con estadísticas anuales de get_user_yearly_stats
        guild: Servidor de Discord

    Returns:
        Embed de Discord con estadísticas wrapped
    """
    year = stats['year']

    embed = discord.Embed(
        title=f"🎵 Tu Wrapped {year}",
        description=f"**{user.display_name}**, este fue tu año musical en **{guild.name}**",
        color=discord.Color.from_rgb(*SPOTIFY_GREEN_RGB)
    )

    embed.set_thumbnail(url=user.display_avatar.url)

    # === TIEMPO TOTAL ESCUCHANDO ===
    total_time = format_time_detailed(stats['total_time_seconds'])
    embed.add_field(
        name="⏱️ Tiempo Total Escuchando",
        value=f"**{total_time}**",
        inline=False
    )

    # === TOP CANCIONES ===
    if stats['top_tracks']:
        top_tracks_text = []
        medals = ["🥇", "🥈", "🥉"] + [f"{i}." for i in range(4, WRAPPED_TOP_TRACKS_LIMIT + 1)]
        for i, track in enumerate(stats['top_tracks'][:WRAPPED_TOP_TRACKS_LIMIT]):
            artist_text = f" - *{track['artist']}*" if track.get('artist') else ""
            top_tracks_text.append(
                f"{medals[i]} **{track['title']}**{artist_text}\n"
                f"   └ {track['play_count']} reproducciones"
            )
        embed.add_field(
            name=f"🎵 Tus Top {WRAPPED_TOP_TRACKS_LIMIT} Canciones",
            value="\n".join(top_tracks_text),
            inline=False
        )

    # === TOP ARTISTAS ===
    if stats['top_artists']:
        top_artists_text = []
        medals = ["🥇", "🥈", "🥉"] + [f"{i}." for i in range(4, WRAPPED_TOP_ARTISTS_LIMIT + 1)]
        for i, artist in enumerate(stats['top_artists'][:WRAPPED_TOP_ARTISTS_LIMIT]):
            time_with_artist = format_duration(artist['total_time'])
            top_artists_text.append(
                f"{medals[i]} **{artist['name']}**\n"
                f"   └ {artist['play_count']} canciones ({time_with_artist})"
            )
        embed.add_field(
            name=f"🎤 Tus Top {WRAPPED_TOP_ARTISTS_LIMIT} Artistas",
            value="\n".join(top_artists_text),
            inline=False
        )

    # === PATRONES DE ESCUCHA ===
    patterns_text = []

    # Hora/período favorito
    if stats['favorite_hour'] is not None:
        period = get_time_period(stats['favorite_hour'])
        period_emoji = get_time_period_emoji(stats['favorite_hour'])
        patterns_text.append(
            f"  {period_emoji} Hora favorita: **{stats['favorite_hour']}:00** ({period})"
        )

    # Día favorito
    if stats['favorite_day_of_week'] is not None:
        day_name = DAY_NAMES.get(stats['favorite_day_of_week'], "Desconocido")
        patterns_text.append(f"  📅 Día favorito: **{day_name}**")

    if patterns_text:
        embed.add_field(
            name="Tus Patrones de Escucha",
            value="\n".join(patterns_text),
            inline=False
        )

    # === VARIEDAD MUSICAL ===
    variety_text = [
        f"  Canciones únicas: **{stats['unique_tracks']:,}**",
        f"  Artistas únicos: **{stats['unique_artists']:,}**",
        f"  Total reproducciones: **{stats['total_plays']:,}**"
    ]
    embed.add_field(
        name="Tu Variedad Musical",
        value="\n".join(variety_text),
        inline=True
    )

    # === RACHAS ===
    streak_text = [
        f"  🔥 Actual: **{stats['current_streak']} días**",
        f"  🏆 Más larga: **{stats['longest_streak']} días**"
    ]
    embed.add_field(
        name="Tus Rachas",
        value="\n".join(streak_text),
        inline=True
    )

    # === PRIMERA CANCIÓN DEL AÑO ===
    if stats['first_track']:
        first_track = stats['first_track']
        artist_text = f" de **{first_track['artist']}**" if first_track.get('artist') else ""
        date_text = first_track['played_at'][:10] if first_track.get('played_at') else ""
        embed.add_field(
            name="🎉 Primera Canción del Año",
            value=f"  *{first_track['title']}*{artist_text}\n  └ {date_text}",
            inline=False
        )

    # === PERSONALIDAD MUSICAL ===
    personality = stats.get('listening_personality', 'Casual Listener')
    personality_emoji = PERSONALITY_EMOJIS.get(personality, "🎵")
    personality_desc = PERSONALITY_DESCRIPTIONS.get(personality, "")

    embed.add_field(
        name=f"{personality_emoji} Personalidad Musical",
        value=f"  **{personality}**\n  *{personality_desc}*",
        inline=False
    )

    # Footer
    embed.set_footer(
        text=f"Wrapped {year} | {guild.name}",
        icon_url=guild.icon.url if guild.icon else None
    )

    embed.timestamp = datetime.now()

    return embed


def create_wrapped_summary_embed(user: discord.Member, stats: Dict[str, Any],
                                 guild: discord.Guild) -> discord.Embed:
    """
    Crea un embed de resumen corto para vista rápida.

    Args:
        user: Miembro de Discord
        stats: Diccionario con estadísticas anuales
        guild: Servidor de Discord

    Returns:
        Embed de Discord con resumen
    """
    year = stats['year']

    embed = discord.Embed(
        title=f"🎵 Wrapped {year} - Resumen",
        description=f"**{user.display_name}** en **{guild.name}**",
        color=discord.Color.from_rgb(*SPOTIFY_GREEN_RGB)
    )

    embed.set_thumbnail(url=user.display_avatar.url)

    # Stats rápidas
    total_time = format_time_detailed(stats['total_time_seconds'])
    top_track = stats['top_tracks'][0] if stats['top_tracks'] else None
    top_artist = stats['top_artists'][0] if stats['top_artists'] else None

    summary = f"⏱️ **{total_time}** de música\n"
    summary += f"🔢 **{stats['total_plays']:,}** reproducciones\n"
    summary += f"🎵 **{stats['unique_tracks']:,}** canciones únicas\n"

    if top_track:
        summary += f"\n🥇 **Canción #1:** {top_track['title']}"
    if top_artist:
        summary += f"\n🎤 **Artista #1:** {top_artist['name']}"

    embed.description = summary

    personality = stats.get('listening_personality', 'Casual Listener')
    personality_emoji = PERSONALITY_EMOJIS.get(personality, "🎵")
    embed.add_field(
        name="Tu Personalidad",
        value=f"{personality_emoji} **{personality}**",
        inline=True
    )

    embed.set_footer(text=f"Usa .wrapped {year} para ver el reporte completo")

    return embed


async def generate_wrapped(user: discord.Member, guild: discord.Guild,
                           year: int = None) -> Optional[discord.Embed]:
    """
    Genera un embed Wrapped para un usuario.

    Args:
        user: Miembro de Discord para generar wrapped
        guild: Servidor de Discord
        year: Año para generar wrapped (por defecto el año actual)

    Returns:
        Embed de Discord o None si no hay datos
    """
    if year is None:
        year = datetime.now().year

    # Obtener estadísticas anuales
    stats = get_user_yearly_stats(user.id, guild.id, year)

    if not stats:
        return None

    return create_wrapped_embed(user, stats, guild)


async def generate_wrapped_comparison(users: List[discord.Member], guild: discord.Guild,
                                      year: int = None) -> Optional[discord.Embed]:
    """
    Genera un embed de comparación Wrapped para múltiples usuarios.

    Args:
        users: Lista de miembros de Discord a comparar
        guild: Servidor de Discord
        year: Año a comparar

    Returns:
        Embed de Discord con comparación o None si no hay datos
    """
    if year is None:
        year = datetime.now().year

    all_stats = []
    for user in users:
        stats = get_user_yearly_stats(user.id, guild.id, year)
        if stats:
            stats['user'] = user
            all_stats.append(stats)

    if not all_stats:
        return None

    embed = discord.Embed(
        title=f"🎵 Wrapped {year} - Comparación",
        description=f"Comparando estadísticas en **{guild.name}**",
        color=discord.Color.gold()
    )

    # Ordenar por tiempo total
    all_stats.sort(key=lambda x: x['total_time_seconds'], reverse=True)

    comparison_text = []
    for i, stats in enumerate(all_stats):
        user = stats['user']
        time_str = format_time_detailed(stats['total_time_seconds'])
        top_artist = stats['top_artists'][0]['name'] if stats['top_artists'] else "N/A"
        comparison_text.append(
            f"**{i+1}. {user.display_name}**\n"
            f"   ⏱️ {time_str}\n"
            f"   🎤 Top artista: {top_artist}\n"
            f"   🔢 {stats['total_plays']:,} reproducciones"
        )

    embed.description = "\n\n".join(comparison_text)

    embed.set_footer(text=f"Wrapped {year} | {guild.name}")
    embed.timestamp = datetime.now()

    return embed
