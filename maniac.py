"""
The Real Seb Bot - Punto de entrada principal
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
from core.config import WRAPPED_ENABLED, SLASH_COMMANDS_GUILD_ID, MAX_RECONNECT_DELAY, BOT_PREFIX

# Importar dashboard web (con manejo de errores si no está disponible)
try:
    from gui.web.dashboard import app as dashboard_app, ensure_log_file
    DASHBOARD_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Dashboard web no disponible: {e}")
    DASHBOARD_AVAILABLE = False


# Configurar logging
logging.getLogger('discord').setLevel(logging.WARNING)

# Configurar logging a archivo
os.makedirs('data', exist_ok=True)
file_handler = logging.FileHandler('data/bot.log', encoding='utf-8', mode='a')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)

# Agregar el file handler al logger raíz
root_logger = logging.getLogger()
root_logger.addHandler(file_handler)
root_logger.setLevel(logging.DEBUG)

# Silenciar logs de Flask/Werkzeug para que no contaminen los logs del bot
# logging.getLogger('werkzeug').setLevel(logging.ERROR)
# logging.getLogger('flask').setLevel(logging.ERROR)

# Variable global para la ventana de logs
log_window = LogWindow()


async def run_bot():
    """Función principal que ejecuta el bot"""
    load_dotenv()
    TOKEN = os.getenv('discord_token')

    intents = discord.Intents.default()
    intents.message_content = True

    bot = commands.Bot(
        command_prefix=BOT_PREFIX,
        intents=intents,
        case_insensitive=True,
        help_command=None,
        max_reconnect_delay=MAX_RECONNECT_DELAY
    )

    @bot.event
    async def on_ready():
        logging.info(f'{bot.user} is now jamming')
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
    async def on_disconnect():
        """Log cuando el bot se desconecta de Discord"""
        logging.warning("Bot desconectado de Discord. Reintentando conexión...")

    @bot.event
    async def on_resumed():
        """Log cuando el bot reanuda la conexión"""
        logging.info("Conexión con Discord reanudada exitosamente.")

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
        try:
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
                if interaction.response.is_done():
                    await interaction.followup.send(
                        "⚠️ Ocurrió un error inesperado.",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        "⚠️ Ocurrió un error inesperado.",
                        ephemeral=True
                    )
        except discord.errors.NotFound:
            # La interacción ya expiró, no se puede responder
            logging.error(f"No se pudo responder al comando - interacción expirada: {error}")

    @bot.command(name="sync", hidden=True)
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
        logging.info("Apagando bot...")
        await shutdown()
        logging.info("Bot apagado correctamente.")


def start_bot():
    """Iniciar el bot en un thread separado"""
    asyncio.run(run_bot())


def start_dashboard():
    """Iniciar el dashboard web en un thread separado"""
    if not DASHBOARD_AVAILABLE:
        return

    try:
        logging.info("=" * 70)
        logging.info("Iniciando Web Dashboard...")
        logging.info("Acceso local:  http://localhost:5000")
        logging.info("Acceso remoto: http://<IP_PUBLICA>:5000")
        logging.info("=" * 70)

        ensure_log_file()
        # use_reloader=False es necesario porque el reloader no funciona en threads
        dashboard_app.run(
            host='0.0.0.0',
            port=5000,
            debug=False,
            threaded=True,
            use_reloader=False
        )
    except Exception as e:
        logging.error(f"Error al iniciar Web Dashboard: {e}")
        logging.info("El bot continuará sin el dashboard.")
        logging.info("Puedes iniciarlo manualmente con: python gui/web/dashboard.py")


if __name__ == "__main__":
    # Iniciar el bot de Discord en un thread separado
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()

    # Iniciar el icono del system tray en un thread separado
    tray_thread = threading.Thread(target=log_window.run_tray, daemon=True)
    tray_thread.start()

    # Iniciar el dashboard web en un thread separado
    if DASHBOARD_AVAILABLE:
        dashboard_thread = threading.Thread(target=start_dashboard, daemon=True)
        dashboard_thread.start()
        logging.info("Dashboard web iniciado en background")
    else:
        logging.warning("Dashboard web no disponible - continuando sin él")

    # Ejecutar la ventana de logs en el thread principal (requerido por tkinter en Windows)
    log_window.run()
