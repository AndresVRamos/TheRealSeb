"""
Sistema de logros/badges para Wrapped en The Real Seb bot
Define criterios y funciones para otorgar achievements
"""
from typing import List, Dict, Any
from dataclasses import dataclass

from core.config import (
    ACHIEVEMENT_MARATHON_HOURS,
    ACHIEVEMENT_CENTURY_CLUB_HOURS,
    ACHIEVEMENT_TIME_TRAVELER_HOURS,
    ACHIEVEMENT_EXPLORER_ARTISTS,
    ACHIEVEMENT_HUNTER_ARTISTS,
    ACHIEVEMENT_VARIETY_TRACKS,
    ACHIEVEMENT_LOYAL_FAN_PLAYS,
    ACHIEVEMENT_SUPER_FAN_PLAYS,
    ACHIEVEMENT_OBSESSED_PLAYS,
    ACHIEVEMENT_WEEK_STREAK_DAYS,
    ACHIEVEMENT_MONTH_STREAK_DAYS,
    ACHIEVEMENT_QUARTER_STREAK_DAYS,
    ACHIEVEMENT_POWER_USER_PLAYS,
    ACHIEVEMENT_MEGA_USER_PLAYS
)


@dataclass
class Achievement:
    """Define un logro desbloqueable"""
    id: str
    name: str
    emoji: str
    description: str
    criteria_check: callable  # Función que recibe stats y retorna bool
    tier: int  # 1=Bronce, 2=Plata, 3=Oro, 4=Platino


# ============================================
# DEFINICIÓN DE ACHIEVEMENTS
# ============================================

ACHIEVEMENTS = [
    # === TIEMPO ⏱️ ===
    Achievement(
        id="marathon_listener",
        name="Maratonista",
        emoji="🏃",
        description=f"Escuchaste más de {ACHIEVEMENT_MARATHON_HOURS} horas",
        criteria_check=lambda s, e=None: s['total_time_seconds'] >= ACHIEVEMENT_MARATHON_HOURS * 3600,
        tier=2
    ),
    Achievement(
        id="century_club",
        name="Century Club",
        emoji="💯",
        description=f"Escuchaste más de {ACHIEVEMENT_CENTURY_CLUB_HOURS} horas",
        criteria_check=lambda s, e=None: s['total_time_seconds'] >= ACHIEVEMENT_CENTURY_CLUB_HOURS * 3600,
        tier=3
    ),
    Achievement(
        id="time_traveler",
        name="Viajero del Tiempo",
        emoji="⏰",
        description=f"Más de {ACHIEVEMENT_TIME_TRAVELER_HOURS} horas de música",
        criteria_check=lambda s, e=None: s['total_time_seconds'] >= ACHIEVEMENT_TIME_TRAVELER_HOURS * 3600,
        tier=4
    ),

    # === EXPLORACIÓN 🔭 ===
    Achievement(
        id="explorer_50",
        name="Explorador Musical",
        emoji="🔭",
        description=f"Descubriste {ACHIEVEMENT_EXPLORER_ARTISTS}+ artistas únicos",
        criteria_check=lambda s, e=None: s['unique_artists'] >= ACHIEVEMENT_EXPLORER_ARTISTS,
        tier=2
    ),
    Achievement(
        id="explorer_100",
        name="Cazador de Artistas",
        emoji="🎯",
        description=f"Descubriste {ACHIEVEMENT_HUNTER_ARTISTS}+ artistas únicos",
        criteria_check=lambda s, e=None: s['unique_artists'] >= ACHIEVEMENT_HUNTER_ARTISTS,
        tier=3
    ),
    Achievement(
        id="variety_master",
        name="Maestro de Variedad",
        emoji="🌈",
        description=f"Escuchaste {ACHIEVEMENT_VARIETY_TRACKS}+ canciones únicas",
        criteria_check=lambda s, e=None: s['unique_tracks'] >= ACHIEVEMENT_VARIETY_TRACKS,
        tier=3
    ),

    # === LEALTAD 💎 ===
    Achievement(
        id="loyal_fan_200",
        name="Fan Leal",
        emoji="💎",
        description=f"{ACHIEVEMENT_LOYAL_FAN_PLAYS}+ plays de tu artista favorito",
        criteria_check=lambda s, e=None: (
            s['top_artists'][0]['play_count'] >= ACHIEVEMENT_LOYAL_FAN_PLAYS
            if s.get('top_artists') else False
        ),
        tier=2
    ),
    Achievement(
        id="super_fan_500",
        name="Súper Fan",
        emoji="⭐",
        description=f"{ACHIEVEMENT_SUPER_FAN_PLAYS}+ plays de tu artista favorito",
        criteria_check=lambda s, e=None: (
            s['top_artists'][0]['play_count'] >= ACHIEVEMENT_SUPER_FAN_PLAYS
            if s.get('top_artists') else False
        ),
        tier=3
    ),
    Achievement(
        id="obsessed",
        name="Obsesionado",
        emoji="🔥",
        description=f"Escuchaste una canción {ACHIEVEMENT_OBSESSED_PLAYS}+ veces",
        criteria_check=lambda s, e=None: (
            s['top_tracks'][0]['play_count'] >= ACHIEVEMENT_OBSESSED_PLAYS
            if s.get('top_tracks') else False
        ),
        tier=3
    ),

    # === RACHAS 🔥 ===
    Achievement(
        id="week_streak",
        name="Racha Semanal",
        emoji="📅",
        description=f"Racha de {ACHIEVEMENT_WEEK_STREAK_DAYS}+ días consecutivos",
        criteria_check=lambda s, e=None: s.get('longest_streak', 0) >= ACHIEVEMENT_WEEK_STREAK_DAYS,
        tier=1
    ),
    Achievement(
        id="month_streak",
        name="Racha Mensual",
        emoji="🌟",
        description=f"Racha de {ACHIEVEMENT_MONTH_STREAK_DAYS}+ días consecutivos",
        criteria_check=lambda s, e=None: s.get('longest_streak', 0) >= ACHIEVEMENT_MONTH_STREAK_DAYS,
        tier=3
    ),
    Achievement(
        id="quarter_streak",
        name="Racha Trimestral",
        emoji="💫",
        description=f"Racha de {ACHIEVEMENT_QUARTER_STREAK_DAYS}+ días consecutivos",
        criteria_check=lambda s, e=None: s.get('longest_streak', 0) >= ACHIEVEMENT_QUARTER_STREAK_DAYS,
        tier=4
    ),

    # === PERSONALIDADES 🎭 ===
    Achievement(
        id="night_owl_badge",
        name="Noctámbulo",
        emoji="🦉",
        description="Tu momento favorito es la noche",
        criteria_check=lambda s, e=None: s.get('listening_personality') == 'Night Owl',
        tier=2
    ),
    Achievement(
        id="early_bird_badge",
        name="Madrugador",
        emoji="🐦",
        description="Empiezas el día con música",
        criteria_check=lambda s, e=None: s.get('listening_personality') == 'Early Bird',
        tier=2
    ),
    Achievement(
        id="explorer_personality",
        name="Espíritu Explorador",
        emoji="🔭",
        description="Siempre buscando nuevos sonidos",
        criteria_check=lambda s, e=None: s.get('listening_personality') == 'Explorer',
        tier=2
    ),
    Achievement(
        id="weekend_warrior_badge",
        name="Guerrero del Fin de Semana",
        emoji="🎉",
        description="Los fines de semana son tu momento musical",
        criteria_check=lambda s, e=None: s.get('listening_personality') == 'Weekend Warrior',
        tier=2
    ),

    # === ACTIVIDAD 📊 ===
    Achievement(
        id="power_user",
        name="Usuario Pro",
        emoji="💪",
        description=f"{ACHIEVEMENT_POWER_USER_PLAYS}+ reproducciones en el año",
        criteria_check=lambda s, e=None: s['total_plays'] >= ACHIEVEMENT_POWER_USER_PLAYS,
        tier=3
    ),
    Achievement(
        id="mega_user",
        name="Usuario Mega",
        emoji="🚀",
        description=f"{ACHIEVEMENT_MEGA_USER_PLAYS}+ reproducciones en el año",
        criteria_check=lambda s, e=None: s['total_plays'] >= ACHIEVEMENT_MEGA_USER_PLAYS,
        tier=4
    ),

    # === ESPECIALES 🎖️ ===
    Achievement(
        id="day_one",
        name="Desde el Día Uno",
        emoji="🎂",
        description="Usaste el bot desde enero",
        criteria_check=lambda s, e=None: (
            s.get('first_play', '')[:7] == f"{s['year']}-01" if s.get('first_play') else False
        ),
        tier=2
    ),
    Achievement(
        id="year_complete",
        name="Año Completo",
        emoji="🏆",
        description="Escuchaste música todos los meses",
        criteria_check=lambda s, e: (
            len(e.get('monthly_breakdown', [])) == 12 if e else False
        ),
        tier=3
    ),
    Achievement(
        id="top_listener",
        name="Top del Servidor",
        emoji="👑",
        description="Eres el oyente #1 del servidor",
        criteria_check=lambda s, e: (
            e.get('rank', {}).get('rank', 0) == 1 if e else False
        ),
        tier=4
    ),
    Achievement(
        id="top_10_percent",
        name="Elite Musical",
        emoji="🎖️",
        description="Estás en el top 10% del servidor",
        criteria_check=lambda s, e: (
            e.get('rank', {}).get('percentile', 1.0) <= 0.10 if e else False
        ),
        tier=2
    ),
]


def get_unlocked_achievements(stats: Dict[str, Any],
                              extended_data: Dict[str, Any] = None) -> List[Achievement]:
    """
    Obtiene la lista de achievements desbloqueados por el usuario.

    Args:
        stats: Diccionario de get_user_yearly_stats
        extended_data: Datos adicionales (monthly_breakdown, rank, etc.)

    Returns:
        Lista de Achievement desbloqueados
    """
    if extended_data is None:
        extended_data = {}

    unlocked = []
    for achievement in ACHIEVEMENTS:
        try:
            # Llamar al criteria_check con stats y extended_data
            if achievement.criteria_check(stats, extended_data):
                unlocked.append(achievement)
        except Exception:
            # Si falla la validación, no se desbloquea
            continue

    # Ordenar por tier descendente (Platino primero)
    return sorted(unlocked, key=lambda a: a.tier, reverse=True)


def get_achievement_progress(stats: Dict[str, Any],
                             extended_data: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Obtiene el progreso hacia achievements no desbloqueados.

    Returns:
        Lista de dicts con:
        - achievement: Achievement
        - progress: float (0.0-1.0)
        - progress_text: str (ej: "87/100 horas")
    """
    if extended_data is None:
        extended_data = {}

    unlocked_ids = {a.id for a in get_unlocked_achievements(stats, extended_data)}
    progress_list = []

    for achievement in ACHIEVEMENTS:
        if achievement.id in unlocked_ids:
            continue  # Ya desbloqueado

        # Calcular progreso para achievements numéricos
        progress = 0.0
        progress_text = ""

        try:
            if "marathon" in achievement.id:
                hours = stats['total_time_seconds'] / 3600
                target = ACHIEVEMENT_MARATHON_HOURS
                progress = min(hours / target, 1.0)
                progress_text = f"{int(hours)}/{target} horas"

            elif "century" in achievement.id:
                hours = stats['total_time_seconds'] / 3600
                target = ACHIEVEMENT_CENTURY_CLUB_HOURS
                progress = min(hours / target, 1.0)
                progress_text = f"{int(hours)}/{target} horas"

            elif "time_traveler" in achievement.id:
                hours = stats['total_time_seconds'] / 3600
                target = ACHIEVEMENT_TIME_TRAVELER_HOURS
                progress = min(hours / target, 1.0)
                progress_text = f"{int(hours)}/{target} horas"

            elif "explorer_50" in achievement.id:
                artists = stats['unique_artists']
                target = ACHIEVEMENT_EXPLORER_ARTISTS
                progress = min(artists / target, 1.0)
                progress_text = f"{artists}/{target} artistas"

            elif "explorer_100" in achievement.id:
                artists = stats['unique_artists']
                target = ACHIEVEMENT_HUNTER_ARTISTS
                progress = min(artists / target, 1.0)
                progress_text = f"{artists}/{target} artistas"

            elif "variety" in achievement.id:
                tracks = stats['unique_tracks']
                target = ACHIEVEMENT_VARIETY_TRACKS
                progress = min(tracks / target, 1.0)
                progress_text = f"{tracks}/{target} canciones"

            elif "loyal_fan" in achievement.id:
                plays = stats['top_artists'][0]['play_count'] if stats.get('top_artists') else 0
                target = ACHIEVEMENT_LOYAL_FAN_PLAYS
                progress = min(plays / target, 1.0)
                progress_text = f"{plays}/{target} plays"

            elif "super_fan" in achievement.id:
                plays = stats['top_artists'][0]['play_count'] if stats.get('top_artists') else 0
                target = ACHIEVEMENT_SUPER_FAN_PLAYS
                progress = min(plays / target, 1.0)
                progress_text = f"{plays}/{target} plays"

            elif "obsessed" in achievement.id:
                plays = stats['top_tracks'][0]['play_count'] if stats.get('top_tracks') else 0
                target = ACHIEVEMENT_OBSESSED_PLAYS
                progress = min(plays / target, 1.0)
                progress_text = f"{plays}/{target} plays"

            elif "streak" in achievement.id:
                streak = stats.get('longest_streak', 0)
                if "week" in achievement.id:
                    target = ACHIEVEMENT_WEEK_STREAK_DAYS
                elif "month" in achievement.id:
                    target = ACHIEVEMENT_MONTH_STREAK_DAYS
                else:
                    target = ACHIEVEMENT_QUARTER_STREAK_DAYS
                progress = min(streak / target, 1.0)
                progress_text = f"{streak}/{target} días"

            elif "power_user" in achievement.id:
                plays = stats['total_plays']
                target = ACHIEVEMENT_POWER_USER_PLAYS
                progress = min(plays / target, 1.0)
                progress_text = f"{plays}/{target} plays"

            elif "mega_user" in achievement.id:
                plays = stats['total_plays']
                target = ACHIEVEMENT_MEGA_USER_PLAYS
                progress = min(plays / target, 1.0)
                progress_text = f"{plays}/{target} plays"

            if progress > 0:
                progress_list.append({
                    'achievement': achievement,
                    'progress': progress,
                    'progress_text': progress_text
                })

        except Exception:
            continue

    # Ordenar por progreso descendente
    return sorted(progress_list, key=lambda x: x['progress'], reverse=True)


def format_achievements_for_embed(unlocked: List[Achievement], max_length: int = 1024) -> str:
    """
    Formatea los achievements para mostrar en un embed con descripciones.

    Args:
        unlocked: Lista de achievements desbloqueados
        max_length: Longitud máxima del string (límite de Discord)

    Returns:
        String con achievements formateados con separación visual y descripciones
    """
    if not unlocked:
        return "*No hay logros desbloqueados este año*"

    # Agrupar por tier
    by_tier = {1: [], 2: [], 3: [], 4: []}
    for achievement in unlocked:
        by_tier[achievement.tier].append(achievement)

    result = []
    tier_names = {4: "💎 Platino", 3: "🥇 Oro", 2: "🥈 Plata", 1: "🥉 Bronce"}

    for tier in [4, 3, 2, 1]:
        if by_tier[tier]:
            # Separador visual antes del tier (excepto el primero)
            if result:
                result.append("")  # Línea en blanco entre tiers

            tier_line = f"**{tier_names[tier]}**"
            if len("\n".join(result + [tier_line])) > max_length - 100:
                break  # No agregar más si nos acercamos al límite

            result.append(tier_line)
            for ach in by_tier[tier]:
                # Formato con bullet y descripción indentada
                ach_line = f"└ {ach.emoji} **{ach.name}**"
                desc_line = f"  └ *{ach.description}*"

                # Verificar que quepan ambas líneas
                if len("\n".join(result + [ach_line, desc_line])) > max_length - 50:
                    result.append("*...y más*")
                    return "\n".join(result)

                result.append(ach_line)
                result.append(desc_line)

    return "\n".join(result)
