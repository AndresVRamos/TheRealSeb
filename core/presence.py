"""
Funciones para manejar la presencia del bot
"""
import discord
import random


async def update_presence(bot, listening: bool, song_title: str = ""):
    """
    Actualiza la presencia del bot

    Args:
        bot: Instancia del bot de Discord
        listening: True si está reproduciendo música, False si no
        song_title: Título de la canción (solo si listening=True)
    """
    if not listening:
        mensajes = [
            "Nada 🦗",
            "Silencio total 🌃"
        ]
    else:
        mensajes = [
            f"{song_title}"
        ]

    mensaje = random.choice(mensajes)
    activity = discord.Activity(
        type=discord.ActivityType.listening,
        name=mensaje
    )
    await bot.change_presence(activity=activity)
