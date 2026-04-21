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
