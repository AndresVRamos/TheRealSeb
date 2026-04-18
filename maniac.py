"""
Music Maniac Bot - Punto de entrada principal
"""
import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
import logging
import threading
from dotenv import load_dotenv

from gui.log_window import LogWindow
from core.config import WRAPPED_ENABLED, SLASH_COMMANDS_GUILD_ID


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

    bot = commands.Bot(command_prefix=".", intents=intents, case_insensitive=True, help_command=None)

    @bot.event
    async def on_ready():
        print(f'{bot.user} is now jamming')
        # Sincronizar slash commands
        try:
            if SLASH_COMMANDS_GUILD_ID:
                guild = discord.Object(id=SLASH_COMMANDS_GUILD_ID)
                bot.tree.copy_global_to(guild=guild)
                synced = await bot.tree.sync(guild=guild)
                logging.info(f"Sincronizados {len(synced)} slash commands en guild {SLASH_COMMANDS_GUILD_ID}")
            else:
                synced = await bot.tree.sync()
                logging.info(f"Sincronizados {len(synced)} slash commands globalmente")
        except Exception as e:
            logging.error(f"Error sincronizando slash commands: {e}")

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

    @bot.tree.error
    async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Manejador de errores para slash commands"""
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"⏳ Comando en cooldown. Intenta de nuevo en {error.retry_after:.1f}s",
                ephemeral=True
            )
        elif isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "🚫 No tienes permisos para usar este comando.",
                ephemeral=True
            )
        else:
            logging.error(f"Error en slash command: {error}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "⚠️ Ocurrió un error inesperado.",
                    ephemeral=True
                )

    @bot.command(name="sync")
    @commands.is_owner()
    async def sync_commands(ctx, scope: str = "guild"):
        """Sincroniza slash commands. Uso: .sync [guild|global]"""
        try:
            if scope == "global":
                synced = await bot.tree.sync()
                await ctx.send(f"✅ Sincronizados {len(synced)} comandos globalmente.")
            else:
                bot.tree.copy_global_to(guild=ctx.guild)
                synced = await bot.tree.sync(guild=ctx.guild)
                await ctx.send(f"✅ Sincronizados {len(synced)} comandos en este servidor.")
        except Exception as e:
            await ctx.send(f"⚠️ Error sincronizando: {e}")

    # Cargar Cogs
    await bot.load_extension('commands.music')
    logging.info("Cog de música cargado correctamente")

    # Cargar Wrapped si está habilitado en config.py
    if WRAPPED_ENABLED:
        await bot.load_extension('commands.wrapped')
        logging.info("Cog de Wrapped cargado correctamente")

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
