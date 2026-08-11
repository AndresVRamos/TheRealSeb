"""
Generador de estadísticas Wrapped para The Real Seb bot
Genera embeds estilo Spotify Wrapped con estadísticas anuales
"""
import discord
from datetime import datetime
from typing import List, Dict, Any

from core.database.queries import (
    get_user_listening_hours,
    get_user_listening_days,
    get_user_monthly_breakdown,
    get_user_records,
    get_user_rank_in_server,
    get_unique_songs_for_user,
    get_artist_discovery_timeline,
    get_favorite_changes,
    get_top_artist_growth,
    get_listening_activity_heatmap
)
from core.formatters import (
    format_duration,
    create_hour_distribution_chart,
    create_comparison_bars
)
from core.achievements import get_unlocked_achievements, format_achievements_for_embed
from core.config import (
    WRAPPED_TOP_TRACKS_LIMIT,
    WRAPPED_TOP_ARTISTS_LIMIT,
    SPOTIFY_GREEN_RGB,
    WRAPPED_MAX_TIMELINE_EVENTS,
    WRAPPED_MAX_FUN_FACTS,
    WRAPPED_MAX_UNIQUE_SONGS_DISPLAY,
    WRAPPED_TRACK_TITLE_MAX_LENGTH,
    TIMELINE_OBSESSION_MIN_PLAYS,
    TIMELINE_TOP_SONG_MIN_PLAYS,
    TIMELINE_MARATHON_MIN_SONGS,
    TIMELINE_DIVERSE_MIN_ARTISTS,
    TIMELINE_REDISCOVERY_MONTHS_GAP
)


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

# Descripciones de personalidades (16 total: 9 existentes + 7 nuevas)
PERSONALITY_DESCRIPTIONS = {
    # Existentes
    "Explorer": "Siempre buscando nuevos sonidos y artistas.",
    "Loyalist": "Tienes tus favoritos y les eres fiel.",
    "Devoted Fan": "Un súper fan de tus artistas favoritos.",
    "Night Owl": "La noche es tu momento para la música.",
    "Early Bird": "Empiezas el día con buena música.",
    "Specialist": "Te enfocas en unos pocos artistas selectos.",
    "Music Enthusiast": "La música es una parte importante de tu vida.",
    "Casual Listener": "Disfrutas la música a tu propio ritmo.",
    "Newcomer": "¡Apenas estás comenzando tu viaje musical!",
    # Nuevas
    "Weekend Warrior": "Los fines de semana son tu momento musical.",
    "Commute Companion": "La música hace tus viajes más llevaderos.",
    "Study Buddy": "Largas sesiones de música para concentrarte.",
    "Party Starter": "Compartes música con otros constantemente.",
    "Hipster": "Descubres artistas antes que nadie.",
}

# Emojis de personalidades
PERSONALITY_EMOJIS = {
    # Existentes
    "Explorer": "🔭",
    "Loyalist": "💎",
    "Devoted Fan": "🌟",
    "Night Owl": "🦉",
    "Early Bird": "🐦",
    "Specialist": "🎯",
    "Music Enthusiast": "🎶",
    "Casual Listener": "😌",
    "Newcomer": "🌱",
    # Nuevas
    "Weekend Warrior": "🎉",
    "Commute Companion": "🚗",
    "Study Buddy": "📚",
    "Party Starter": "🎊",
    "Hipster": "🕶️",
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




# ============================================
# FUNCIONES GENERADORAS DE SECCIONES WRAPPED
# ============================================

def truncate_text(text: str, max_length: int) -> str:
    """Trunca texto agregando '...' si excede longitud."""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def create_intro_section(user: discord.Member, stats: Dict[str, Any],
                         guild: discord.Guild) -> discord.Embed:
    """Sección 0: Intro - Resumen general y personalidad"""
    year = stats['year']

    embed = discord.Embed(
        title=f"🎵 Tu Wrapped {year}",
        description=f"**{user.display_name}**, este fue tu año musical",
        color=discord.Color.from_rgb(*SPOTIFY_GREEN_RGB)
    )

    embed.set_thumbnail(url=user.display_avatar.url)

    # Tiempo total
    total_time = format_time_detailed(stats['total_time_seconds'])
    embed.add_field(
        name="⏱️ Tiempo Escuchando",
        value=f"**{total_time}**",
        inline=True
    )

    # Reproducciones
    embed.add_field(
        name="🔢 Reproducciones",
        value=f"**{stats['total_plays']:,}**",
        inline=True
    )

    # Variedad
    embed.add_field(
        name="🎵 Variedad",
        value=f"**{stats['unique_tracks']:,}** canciones\n**{stats['unique_artists']:,}** artistas",
        inline=True
    )

    # Personalidad musical (destacado)
    personality = stats.get('listening_personality', 'Casual Listener')
    personality_emoji = PERSONALITY_EMOJIS.get(personality, "🎵")
    personality_desc = PERSONALITY_DESCRIPTIONS.get(personality, "")

    embed.add_field(
        name=f"{personality_emoji} Tu Personalidad Musical",
        value=f"**{personality}**\n*{personality_desc}*",
        inline=False
    )

    embed.set_footer(
        text=f"Wrapped {year} | {guild.name} | Navega con ◀ ▶",
        icon_url=guild.icon.url if guild.icon else None
    )

    return embed


def create_top_songs_section(user: discord.Member, stats: Dict[str, Any],
                             guild: discord.Guild) -> discord.Embed:
    """Sección 1: Top Songs - Top 5 canciones"""
    year = stats['year']

    embed = discord.Embed(
        title=f"🎵 Tus Top {WRAPPED_TOP_TRACKS_LIMIT} Canciones {year}",
        description=f"Las canciones que más escuchaste",
        color=discord.Color.from_rgb(*SPOTIFY_GREEN_RGB)
    )

    embed.set_thumbnail(url=user.display_avatar.url)

    if stats['top_tracks']:
        medals = ["🥇", "🥈", "🥉"] + [f"{i}." for i in range(4, WRAPPED_TOP_TRACKS_LIMIT + 1)]
        for i, track in enumerate(stats['top_tracks'][:WRAPPED_TOP_TRACKS_LIMIT]):
            title = truncate_text(track['title'], WRAPPED_TRACK_TITLE_MAX_LENGTH)
            artist_text = f" - *{track['artist']}*" if track.get('artist') else ""

            embed.add_field(
                name=f"{medals[i]} {title}{artist_text}",
                value=f"**{track['play_count']}** reproducciones",
                inline=False
            )
    else:
        embed.description = "*No hay canciones registradas este año*"

    embed.set_footer(text=f"Wrapped {year} | {guild.name}")

    return embed


def create_top_artists_section(user: discord.Member, stats: Dict[str, Any],
                               guild: discord.Guild) -> discord.Embed:
    """Sección 2: Top Artists - Top 5 artistas"""
    year = stats['year']

    embed = discord.Embed(
        title=f"🎤 Tus Top {WRAPPED_TOP_ARTISTS_LIMIT} Artistas {year}",
        description=f"Los artistas que dominaron tu año",
        color=discord.Color.from_rgb(*SPOTIFY_GREEN_RGB)
    )

    embed.set_thumbnail(url=user.display_avatar.url)

    if stats['top_artists']:
        medals = ["🥇", "🥈", "🥉"] + [f"{i}." for i in range(4, WRAPPED_TOP_ARTISTS_LIMIT + 1)]
        for i, artist in enumerate(stats['top_artists'][:WRAPPED_TOP_ARTISTS_LIMIT]):
            time_with_artist = format_duration(artist['total_time'])

            embed.add_field(
                name=f"{medals[i]} {artist['name']}",
                value=f"**{artist['play_count']}** canciones • {time_with_artist}",
                inline=False
            )
    else:
        embed.description = "*No hay artistas registrados este año*"

    embed.set_footer(text=f"Wrapped {year} | {guild.name}")

    return embed


def create_stats_section(user: discord.Member, stats: Dict[str, Any],
                        extended_data: Dict[str, Any], guild: discord.Guild) -> discord.Embed:
    """Sección 3: Stats & Records - Estadísticas y récords"""
    year = stats['year']

    embed = discord.Embed(
        title=f"📊 Tus Estadísticas {year}",
        description=f"Tus números y récords personales",
        color=discord.Color.from_rgb(*SPOTIFY_GREEN_RGB)
    )

    embed.set_thumbnail(url=user.display_avatar.url)

    # Variedad musical
    variety_text = [
        f"🎵 **{stats['unique_tracks']:,}** canciones únicas",
        f"🎤 **{stats['unique_artists']:,}** artistas únicos",
        f"🔢 **{stats['total_plays']:,}** reproducciones totales"
    ]
    embed.add_field(
        name="Tu Variedad Musical",
        value="\n".join(variety_text),
        inline=False
    )

    # Rachas
    streak_text = [
        f"🔥 Racha actual: **{stats.get('current_streak', 0)} días**",
        f"🏆 Racha más larga: **{stats.get('longest_streak', 0)} días**"
    ]
    embed.add_field(
        name="Tus Rachas",
        value="\n".join(streak_text),
        inline=False
    )

    # Récords personales
    records = extended_data.get('records', {})
    if records and records.get('busiest_day'):
        busiest = records['busiest_day']
        longest = records.get('longest_track')

        records_text = []
        records_text.append(f"📅 Día más activo: **{busiest['date']}**")
        records_text.append(f"   └ {busiest['plays_count']} canciones")

        if longest:
            longest_title = truncate_text(longest['title'], 40)
            records_text.append(f"⏱️ Canción más larga: *{longest_title}*")

        embed.add_field(
            name="Récords Personales",
            value="\n".join(records_text),
            inline=False
        )

    # Patrones de escucha
    if stats.get('favorite_hour') is not None:
        period = get_time_period(stats['favorite_hour'])
        period_emoji = get_time_period_emoji(stats['favorite_hour'])
        day_name = DAY_NAMES.get(stats.get('favorite_day_of_week', 0), "")

        patterns_text = [
            f"{period_emoji} Hora favorita: **{stats['favorite_hour']}:00** ({period})",
            f"📅 Día favorito: **{day_name}**"
        ]
        embed.add_field(
            name="Tus Patrones",
            value="\n".join(patterns_text),
            inline=False
        )

    embed.set_footer(text=f"Wrapped {year} | {guild.name}")

    return embed


def create_timeline_section(user: discord.Member, stats: Dict[str, Any],
                            extended_data: Dict[str, Any], guild: discord.Guild) -> discord.Embed:
    """Sección 4: Timeline - Eventos mes a mes con múltiples tipos de eventos"""
    year = stats['year']

    embed = discord.Embed(
        title=f"📅 Tu Timeline Musical {year}",
        description=f"Los momentos destacados de tu año",
        color=discord.Color.from_rgb(*SPOTIFY_GREEN_RGB)
    )

    embed.set_thumbnail(url=user.display_avatar.url)

    month_names = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN",
                   "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]

    # Obtener datos necesarios
    monthly_breakdown = extended_data.get('monthly_breakdown', [])
    discovery_timeline = extended_data.get('discovery_timeline', [])

    events = []
    processed_months = set()  # Para evitar duplicados del mismo mes

    # 1. Primera canción del año (siempre al inicio si existe)
    if stats.get('first_track'):
        first = stats['first_track']
        first_title = truncate_text(first['title'], 35)
        events.append((0, 0, f"🎉 **Primera canción:** *{first_title}*"))

    # 2. Encontrar mes más activo
    if monthly_breakdown:
        max_plays_month = max(monthly_breakdown, key=lambda m: m.get('total_plays', 0))
        if max_plays_month.get('total_plays', 0) > 0:
            month = max_plays_month['month']
            month_name = month_names[month - 1]
            plays = max_plays_month['total_plays']
            events.append((month, 1, f"**{month_name}:** Tu mes más activo ({plays} canciones) 🔥"))
            processed_months.add((month, 'active'))

    # 3. Procesar eventos por mes
    for month_data in monthly_breakdown:
        month = month_data['month']
        month_name = month_names[month - 1]

        # 3a. Descubrimiento de nuevos artistas
        if month_data.get('new_artists', 0) > 0:
            discovered = [d for d in discovery_timeline if d['month'] == month]
            if discovered:
                artist_name = truncate_text(discovered[0]['artist_name'], 30)
                events.append((month, 2, f"**{month_name}:** Descubriste a *{artist_name}* 🔭"))

        # 3b. Obsesión del mes (umbral reducido a 8)
        if month_data.get('top_track') and month_data['top_track']['play_count'] >= TIMELINE_OBSESSION_MIN_PLAYS:
            track = month_data['top_track']
            track_title = truncate_text(track['title'], 35)
            events.append((
                month, 3,
                f"**{month_name}:** Obsesión con *{track_title}* ({track['play_count']} plays) 🔥"
            ))
        # 3c. Canción del mes (más permisivo, 5+ plays)
        elif month_data.get('top_track') and month_data['top_track']['play_count'] >= TIMELINE_TOP_SONG_MIN_PLAYS:
            track = month_data['top_track']
            track_title = truncate_text(track['title'], 35)
            events.append((
                month, 4,
                f"**{month_name}:** Canción del mes: *{track_title}* ({track['play_count']} plays) 🎵"
            ))

        # 3d. Mes diverso (10+ artistas únicos)
        if month_data.get('unique_artists', 0) >= TIMELINE_DIVERSE_MIN_ARTISTS:
            artists_count = month_data['unique_artists']
            events.append((
                month, 5,
                f"**{month_name}:** Mes diverso ({artists_count} artistas diferentes) 🌈"
            ))

        # 3e. Maratón musical (día con 15+ canciones)
        if month_data.get('busiest_day_plays', 0) >= TIMELINE_MARATHON_MIN_SONGS:
            day_plays = month_data['busiest_day_plays']
            events.append((
                month, 6,
                f"**{month_name}:** Maratón musical ({day_plays} canciones en un día) 🎧"
            ))

    # 4. Cambios de favorito y Redescubrimientos
    # Estos eventos requieren queries adicionales más detalladas
    # TODO: Implementar cuando se creen queries que devuelvan listas de cambios

    # Ordenar eventos por mes y prioridad
    events.sort(key=lambda x: (x[0], x[1]))

    # Formatear eventos (quitar tuplas de ordenamiento)
    formatted_events = [event[2] for event in events]

    if formatted_events:
        embed.description = "\n\n".join(formatted_events[:WRAPPED_MAX_TIMELINE_EVENTS])
    else:
        embed.description = "*No hay eventos destacados este año*"

    embed.set_footer(text=f"Wrapped {year} | {guild.name}")

    return embed


def create_achievements_section(user: discord.Member, stats: Dict[str, Any],
                                extended_data: Dict[str, Any], guild: discord.Guild) -> discord.Embed:
    """Sección 5: Achievements - Badges desbloqueados"""
    year = stats['year']

    embed = discord.Embed(
        title=f"🏆 Tus Logros {year}",
        description=f"Achievements desbloqueados este año",
        color=discord.Color.from_rgb(*SPOTIFY_GREEN_RGB)
    )

    embed.set_thumbnail(url=user.display_avatar.url)

    # Obtener achievements desbloqueados
    unlocked = get_unlocked_achievements(stats, extended_data)

    if unlocked:
        achievements_text = format_achievements_for_embed(unlocked, max_length=900)
        embed.add_field(
            name=f"🎖️ {len(unlocked)} Logros Desbloqueados",
            value=achievements_text,
            inline=False
        )
    else:
        embed.description = "*No hay logros desbloqueados este año*\n¡Sigue escuchando música para desbloquearlos!"

    embed.set_footer(text=f"Wrapped {year} | {guild.name}")

    return embed


def create_fun_facts_section(user: discord.Member, stats: Dict[str, Any],
                             extended_data: Dict[str, Any], guild: discord.Guild) -> discord.Embed:
    """Sección 6: Fun Facts - Comparaciones creativas y datos curiosos"""
    year = stats['year']

    embed = discord.Embed(
        title=f"🎪 Datos Curiosos {year}",
        description=f"Datos interesantes sobre tu año musical",
        color=discord.Color.from_rgb(*SPOTIFY_GREEN_RGB)
    )

    embed.set_thumbnail(url=user.display_avatar.url)

    # Comparaciones creativas
    total_hours = stats['total_time_seconds'] / 3600
    comparisons = []

    if total_hours >= 24:
        days = total_hours / 24
        comparisons.append(f"🌍 Eso es **{days:.1f} días** de música continua!")

    if total_hours >= 50:
        distance_km = total_hours * 5  # Asumiendo 5 km/h caminando
        comparisons.append(f"🚶 Podrías haber caminado **{int(distance_km)} km**")

    if total_hours >= 2:
        movies = total_hours / 2
        comparisons.append(f"🎬 Podrías ver **{int(movies)} películas** en ese tiempo")

    if stats['total_time_seconds'] >= 180:
        songs = stats['total_time_seconds'] / 210
        comparisons.append(f"🎵 Aproximadamente **{int(songs)} canciones** promedio")

    if comparisons:
        embed.add_field(
            name="Comparaciones",
            value="\n".join(comparisons[:4]),
            inline=False
        )

    # Gráfico de distribución horaria
    hour_data = get_user_listening_hours(user.id, guild.id, year)
    if hour_data:
        chart = create_hour_distribution_chart(hour_data, max_width=15)
        embed.add_field(
            name="📊 Tu Distribución por Hora",
            value=f"```\n{chart}\n```",
            inline=False
        )

    # Fun facts dinámicos
    fun_facts = generate_dynamic_fun_facts(stats, extended_data)
    if fun_facts:
        embed.add_field(
            name="💡 Sabías que...",
            value="\n".join(fun_facts[:WRAPPED_MAX_FUN_FACTS]),
            inline=False
        )

    embed.set_footer(text=f"Wrapped {year} | {guild.name}")

    return embed


def create_rankings_section(user: discord.Member, stats: Dict[str, Any],
                            extended_data: Dict[str, Any], guild: discord.Guild) -> discord.Embed:
    """Sección 7: Rankings - Posición en el servidor"""
    year = stats['year']

    embed = discord.Embed(
        title=f"📈 Tu Ranking {year}",
        description=f"Tu posición en **{guild.name}**",
        color=discord.Color.from_rgb(*SPOTIFY_GREEN_RGB)
    )

    embed.set_thumbnail(url=user.display_avatar.url)

    rank_data = extended_data.get('rank', {})

    if rank_data and rank_data.get('rank', 0) > 0:
        rank = rank_data['rank']
        total_users = rank_data['total_users']
        percentile = rank_data['percentile']
        comparison_ratio = rank_data.get('comparison_ratio', 0)

        # Posición
        rank_emoji = "👑" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else "📊"
        embed.add_field(
            name=f"{rank_emoji} Tu Posición",
            value=f"**#{rank}** de **{total_users}** oyentes",
            inline=False
        )

        # Percentil
        percentile_pct = int(percentile * 100)
        embed.add_field(
            name="📊 Percentil",
            value=f"Top **{percentile_pct}%** del servidor",
            inline=True
        )

        # Comparación con promedio
        if comparison_ratio > 0:
            embed.add_field(
                name="📈 vs Promedio",
                value=f"**{comparison_ratio:.1f}x** más que el promedio",
                inline=True
            )

        # Mensaje motivacional
        if rank == 1:
            message = "¡Eres el oyente #1 del servidor! 👑"
        elif rank <= 3:
            message = "¡Estás en el podio! 🏆"
        elif percentile <= 0.10:
            message = "¡Eres parte de la élite musical! 🎖️"
        elif percentile <= 0.25:
            message = "¡Excelente actividad musical! ⭐"
        else:
            message = "¡Sigue escuchando música! 🎵"

        embed.add_field(
            name="💬",
            value=f"*{message}*",
            inline=False
        )
    else:
        embed.description = "*No hay suficientes datos de ranking este año*"

    embed.set_footer(text=f"Wrapped {year} | {guild.name}")

    return embed


def create_only_you_section(user: discord.Member, stats: Dict[str, Any],
                            extended_data: Dict[str, Any], guild: discord.Guild) -> discord.Embed:
    """Sección 8: Solo Tú - Canciones únicas del usuario"""
    year = stats['year']

    embed = discord.Embed(
        title=f"🦄 Solo Tú {year}",
        description=f"Canciones que solo tú escuchaste",
        color=discord.Color.from_rgb(*SPOTIFY_GREEN_RGB)
    )

    embed.set_thumbnail(url=user.display_avatar.url)

    unique_songs = extended_data.get('unique_songs', [])

    if unique_songs:
        songs_text = []
        for i, song in enumerate(unique_songs[:WRAPPED_MAX_UNIQUE_SONGS_DISPLAY], 1):
            title = truncate_text(song['track_title'], 40)
            artist = f" - *{song['artist_name']}*" if song.get('artist_name') else ""
            songs_text.append(f"{i}. **{title}**{artist}")

        embed.add_field(
            name=f"🎵 Tus Canciones Exclusivas ({len(unique_songs)} total)",
            value="\n".join(songs_text),
            inline=False
        )

        embed.add_field(
            name="💎",
            value="*¡Eres el único fan de estas canciones en el servidor!*",
            inline=False
        )
    else:
        embed.description = "*Todas tus canciones también fueron escuchadas por otros*\n¡Comparten gustos musicales!"

    embed.set_footer(text=f"Wrapped {year} | {guild.name}")

    return embed


def generate_dynamic_fun_facts(stats: Dict[str, Any],
                               extended_data: Dict[str, Any]) -> List[str]:
    """
    Genera datos curiosos dinámicos basados en estadísticas.

    Args:
        stats: Estadísticas anuales básicas
        extended_data: Datos extendidos

    Returns:
        Lista de strings con fun facts
    """
    facts = []

    # 1. Cambios de canción favorita
    fav_changes = extended_data.get('favorite_changes', 0)
    if fav_changes > 0:
        facts.append(f"• Tu canción favorita cambió **{fav_changes} veces** este año")

    # 2. Frecuencia de descubrimientos
    discovery_timeline = extended_data.get('discovery_timeline', [])
    if len(discovery_timeline) > 0:
        days_per_discovery = 365 / len(discovery_timeline)
        if days_per_discovery < 1:
            facts.append(f"• Descubriste un nuevo artista **casi a diario** ({len(discovery_timeline)} artistas)")
        else:
            facts.append(f"• Descubriste un nuevo artista cada **{int(days_per_discovery)} días**")

    # 3. Día favorito de la semana
    if stats.get('favorite_day_of_week') is not None:
        day_names_lower = ["domingos", "lunes", "martes", "miércoles", "jueves", "viernes", "sábados"]
        day_name = day_names_lower[stats['favorite_day_of_week']]
        facts.append(f"• Escuchaste más los **{day_name}**")

    # 4. Crecimiento del artista #1
    growth = extended_data.get('top_artist_growth', {})
    if growth.get('growth_percentage', 0) > 100:
        facts.append(
            f"• Tu artista #1 creció **{int(growth['growth_percentage'])}%** vs año pasado"
        )

    # 5. Récord de día más activo
    records = extended_data.get('records', {})
    busiest_day = records.get('busiest_day')
    if busiest_day:
        facts.append(
            f"• Tu día más activo: **{busiest_day['date']}** con {busiest_day['plays_count']} canciones"
        )

    # 6. Variedad vs consistencia
    if stats['total_plays'] > 0:
        variety_ratio = stats['unique_tracks'] / stats['total_plays']
        if variety_ratio > 0.7:
            facts.append(f"• Raramente repites canciones (**{int(variety_ratio*100)}%** variedad)")
        elif variety_ratio < 0.3:
            facts.append(f"• Te gusta repetir tus favoritas (**{int((1-variety_ratio)*100)}%** repeticiones)")

    return facts
