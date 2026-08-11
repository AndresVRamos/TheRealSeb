"""
Funciones helper para formateo de tiempo, barras de progreso y utilidades de Discord
"""
import re
import logging

import discord

from core.config import PROGRESS_BAR_LENGTH, PROGRESS_BAR_FILLED, PROGRESS_BAR_EMPTY


def format_duration(seconds):
    """Convierte segundos a formato HH:MM:SS o MM:SS"""
    if seconds == 0:
        return "N/A"
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}" if hours > 0 else f"{minutes:02}:{seconds:02}"


def parse_time_string(time_str):
    """
    Convierte strings de tiempo como '1m30s', '90s', '5m', '1:30' a segundos
    """
    try:
        time_str = time_str.lower().strip()
        total_seconds = 0

        # Formato MM:SS o HH:MM:SS
        if ':' in time_str:
            parts = time_str.split(':')
            if len(parts) == 2:  # MM:SS
                minutes, seconds = map(int, parts)
                total_seconds = minutes * 60 + seconds
            elif len(parts) == 3:  # HH:MM:SS
                hours, minutes, seconds = map(int, parts)
                total_seconds = hours * 3600 + minutes * 60 + seconds
            else:
                return None
        else:
            # Formato con sufijos (5m, 30s, 1m30s)
            # Buscar horas (h)
            hours_match = re.search(r'(\d+)h', time_str)
            if hours_match:
                total_seconds += int(hours_match.group(1)) * 3600
                time_str = re.sub(r'\d+h', '', time_str)

            # Buscar minutos (m)
            minutes_match = re.search(r'(\d+)m', time_str)
            if minutes_match:
                total_seconds += int(minutes_match.group(1)) * 60
                time_str = re.sub(r'\d+m', '', time_str)

            # Buscar segundos (s)
            seconds_match = re.search(r'(\d+)s', time_str)
            if seconds_match:
                total_seconds += int(seconds_match.group(1))
                time_str = re.sub(r'\d+s', '', time_str)

            # Si queda algo que sea solo número, asumimos que son segundos
            remaining = re.sub(r'\s+', '', time_str)
            if remaining.isdigit():
                total_seconds += int(remaining)
            elif remaining and not total_seconds:
                # Si no se pudo parsear nada y queda texto
                return None

        return total_seconds if total_seconds > 0 else None

    except (ValueError, AttributeError):
        return None


def create_progress_bar(current, total, bar_length=PROGRESS_BAR_LENGTH):
    """Crea una barra de progreso visual"""
    if total == 0:
        return PROGRESS_BAR_EMPTY * bar_length
    progress = int((current / total) * bar_length)
    return PROGRESS_BAR_FILLED * progress + PROGRESS_BAR_EMPTY * (bar_length - progress)


async def safe_edit_message(message: discord.Message, **kwargs) -> discord.Message:
    """
    Edita un mensaje de Discord, con fallback si el token de interacción expiró.

    Cuando un mensaje fue creado por una interacción (slash command), el token
    expira después de 15 minutos. Este helper detecta ese error y recupera el
    mensaje vía fetch_message para editarlo usando el token del bot.

    Args:
        message: El mensaje a editar
        **kwargs: Argumentos para message.edit() (embed, view, content, etc.)

    Returns:
        El mensaje editado (puede ser el original o uno nuevo si hubo fallback)

    Raises:
        discord.errors.HTTPException: Si el error no es de token expirado
    """
    try:
        await message.edit(**kwargs)
        return message
    except discord.errors.HTTPException as e:
        if e.code == 50027 or e.status == 401:
            logging.debug("Token de interacción expirado, recuperando mensaje vía fetch_message...")
            msg = await message.channel.fetch_message(message.id)
            await msg.edit(**kwargs)
            return msg
        raise


# ============================================
# GRÁFICOS ASCII PARA WRAPPED
# ============================================

def create_hour_distribution_chart(hour_data: dict[int, int], max_width: int = 20) -> str:
    """
    Crea un gráfico de barras horizontales para distribución por hora (agrupado cada 2 horas).

    Args:
        hour_data: Dict {hour: play_count} (0-23)
        max_width: Ancho máximo de las barras

    Returns:
        String con gráfico ASCII (12 líneas máx)

    Ejemplo:
        00-02 ▓▓░░░░░░░░░░░░░░░░░░ 5
        02-04 ░░░░░░░░░░░░░░░░░░░░ 1
    """
    if not hour_data:
        return "*Sin datos*"

    # Agrupar por bloques de 2 horas
    grouped_data = {}
    for hour in range(0, 24, 2):
        count = hour_data.get(hour, 0) + hour_data.get(hour + 1, 0)
        grouped_data[hour] = count

    max_plays = max(grouped_data.values()) if grouped_data else 1
    lines = []

    for hour in range(0, 24, 2):
        plays = grouped_data.get(hour, 0)
        bar_length = int((plays / max_plays) * max_width) if max_plays > 0 else 0
        filled = "▓" * bar_length
        empty = "░" * (max_width - bar_length)
        lines.append(f"{hour:02d}-{hour+2:02d} {filled}{empty} {plays}")

    return "\n".join(lines)


def create_activity_heatmap(heatmap_data: dict[int, dict[int, int]]) -> str:
    """
    Crea un mapa de calor de actividad semanal (simplificado cada 3 horas).

    Args:
        heatmap_data: Dict {day_of_week: {hour: play_count}}

    Returns:
        String con mapa de calor ASCII

    Ejemplo:
        📅      00 03 06 09 12 15 18 21
        Dom     ░░ ░░ ░░ ▓▓ ▓▓ ░░ ▓▓ ▓▓
        Lun     ░░ ░░ ▓▓ ▓▓ ░░ ░░ ▓▓ ░░
    """
    if not heatmap_data:
        return "*Sin datos*"

    day_names = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"]

    # Calcular máximo global para normalizar
    max_plays = 0
    for day_data in heatmap_data.values():
        max_plays = max(max_plays, max(day_data.values()) if day_data else 0)

    if max_plays == 0:
        return "*Sin datos*"

    # Dividir en 4 niveles de intensidad
    def get_intensity_char(plays):
        if plays == 0:
            return "░░"
        ratio = plays / max_plays
        if ratio > 0.75:
            return "▓▓"
        elif ratio > 0.5:
            return "▒▒"
        elif ratio > 0.25:
            return "▒░"
        else:
            return "░▓"

    # Header con horas (cada 3 horas)
    lines = ["📅      " + " ".join(f"{h:02d}" for h in range(0, 24, 3))]

    # Fila por día
    for day in range(7):
        day_data = heatmap_data.get(day, {})
        row = f"{day_names[day]:3s}     "
        for hour in range(0, 24, 3):
            # Agrupar las 3 horas siguientes
            plays = sum(day_data.get(h, 0) for h in range(hour, min(hour + 3, 24)))
            row += get_intensity_char(plays) + " "
        lines.append(row.rstrip())

    return "\n".join(lines)


def create_evolution_chart(monthly_data: list[dict[str, any]],
                           metric: str = "total_plays") -> str:
    """
    Crea un gráfico de línea ASCII de evolución mensual (simplificado).

    Args:
        monthly_data: Lista de 12 dicts con datos mensuales
        metric: Métrica a graficar (total_plays, total_hours, unique_artists)

    Returns:
        String con gráfico ASCII

    Ejemplo:
        125 │         ╭─╮
        100 │       ╭─╯ ╰╮
         75 │     ╭─╯    ╰─╮
         50 │   ╭─╯        ╰─╮
         25 │╭──╯            ╰──
          0 └─────────────────────
            E F M A M J J A S O N D
    """
    if not monthly_data or len(monthly_data) == 0:
        return "*Sin datos*"

    month_abbrev = ["E", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]

    # Extraer valores
    values = []
    for i in range(1, 13):
        month_data = next((m for m in monthly_data if m['month'] == i), None)
        if month_data:
            val = month_data.get(metric, 0)
            # Si es total_hours, ya viene en horas
            values.append(val)
        else:
            values.append(0)

    max_val = max(values) if values and max(values) > 0 else 1

    # Normalizar a altura de 5 filas
    height = 5
    normalized = [int((v / max_val) * height) if max_val > 0 else 0 for v in values]

    # Crear gráfico
    lines = []
    for level in range(height, -1, -1):
        y_val = int(max_val * level / height) if max_val > 0 else 0
        y_label = f"{y_val:>3d} │"
        row = ""
        for i, val in enumerate(normalized):
            if val > level:
                row += "▓"
            elif val == level and level > 0:
                row += "▒"
            else:
                row += " "
        lines.append(y_label + row)

    # Eje X
    lines.append("  0 └" + "─" * 12)
    lines.append("    " + "".join(month_abbrev))

    return "\n".join(lines)


def create_comparison_bars(user1_value: float, user2_value: float,
                           user1_name: str, user2_name: str,
                           label: str, max_width: int = 15,
                           value_type: str = "hours") -> str:
    """
    Crea barras de comparación para Wrapped Battle.

    Args:
        user1_value, user2_value: Valores a comparar
        user1_name, user2_name: Nombres de usuarios (truncados a 10 chars)
        label: Etiqueta de la categoría
        max_width: Ancho máximo de barra
        value_type: Tipo de valor ("hours", "count", "days")

    Returns:
        String con barras de comparación

    Ejemplo:
        ⏱️ Tiempo Total
        Andrés  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ 245h
        Carlos  ▓▓▓▓▓▓▓░░░░░░░░░ 120h
        🏆 Andrés gana!
    """
    max_val = max(user1_value, user2_value)
    if max_val == 0:
        return f"**{label}**\n*Empate (0-0)*"

    bar1_len = int((user1_value / max_val) * max_width)
    bar2_len = int((user2_value / max_val) * max_width)

    bar1 = "▓" * bar1_len + "░" * (max_width - bar1_len)
    bar2 = "▓" * bar2_len + "░" * (max_width - bar2_len)

    # Formatear valores según tipo
    if value_type == "hours":
        val1_str = f"{int(user1_value / 3600)}h"
        val2_str = f"{int(user2_value / 3600)}h"
    elif value_type == "days":
        val1_str = f"{int(user1_value)}d"
        val2_str = f"{int(user2_value)}d"
    else:  # count
        val1_str = f"{int(user1_value)}"
        val2_str = f"{int(user2_value)}"

    # Truncar nombres a 10 chars
    user1_display = user1_name[:10]
    user2_display = user2_name[:10]

    # Determinar ganador
    if user1_value > user2_value:
        winner = f"🏆 {user1_display} gana!"
    elif user2_value > user1_value:
        winner = f"🏆 {user2_display} gana!"
    else:
        winner = "🤝 Empate!"

    return (f"**{label}**\n"
            f"{user1_display:10s} {bar1} {val1_str}\n"
            f"{user2_display:10s} {bar2} {val2_str}\n"
            f"{winner}")
