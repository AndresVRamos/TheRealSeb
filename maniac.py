"""
Music Maniac Bot - Punto de entrada principal
"""
import discord
from discord.ext import commands
import os
import asyncio
import logging
import threading
from dotenv import load_dotenv

from gui.log_window import LogWindow


# Configurar logging
logging.getLogger('discord').setLevel(logging.WARNING)

# Variable global para la ventana de logs
log_window = LogWindow()


async def run_bot():
    """Función principal que ejecuta el bot"""
    load_dotenv()
    TOKEN = os.getenv('discord_token')

    intents = discord.Intents.default()
    intents.message_content = True

    bot = commands.Bot(command_prefix=".", intents=intents, case_insensitive=True)

    @bot.event
    async def on_ready():
        print(f'{bot.user} is now jamming')

    @bot.event
    async def on_command_error(ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            if ctx.command.name == "move":
                await ctx.send(f"Faltan argumentos. Usa: `{ctx.prefix}move <de> <a>`")
            else:
                await ctx.send(f"Falta el enlace o nombre de la canción. Usa: `{ctx.prefix}{ctx.command.name} <canción>`")
        elif isinstance(error, commands.CommandInvokeError):
            logging.error(f"Error ejecutando comando {ctx.command.name}: {error.original}")
            if isinstance(error.original, discord.HTTPException) and error.original.code == 50035:
                logging.error("Error de Embed: El contenido era demasiado grande.")
            else:
                await ctx.send("Ocurrió un error inesperado al ejecutar el comando.")
        else:
            logging.error(f"Error no manejado: {error}")

    # Cargar Cogs
    await bot.load_extension('commands.music')
    logging.info("Cog de música cargado correctamente")

    async def shutdown():
        """Función para cerrar el bot limpiamente"""
        music_cog = bot.get_cog('MusicCommands')
        if music_cog:
            for vc in music_cog.voice_clients.values():
                await vc.disconnect()
        await bot.close()

    try:
        await bot.start(TOKEN)
    except KeyboardInterrupt:
        print("Apagando bot...")
        await shutdown()
        print("Bot apagado correctamente.")


def start_bot():
    """Iniciar el bot en un thread separado"""
    asyncio.run(run_bot())


if __name__ == "__main__":
    # Iniciar el bot de Discord en un thread separado
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()

    # Iniciar el icono del system tray en un thread separado
    tray_thread = threading.Thread(target=log_window.run_tray, daemon=True)
    tray_thread.start()

    # Ejecutar la ventana de logs en el thread principal (requerido por tkinter en Windows)
    log_window.run()
