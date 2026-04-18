"""
Decoradores personalizados para comandos
"""


def command_category(category: str):
    """
    Decorador que asigna una categoría a un comando para el menú de ayuda.

    Categorías disponibles:
    - playback: Comandos de reproducción (play, add, search, etc.)
    - control: Controles de reproducción (pause, resume, skip, etc.)
    - queue: Gestión de cola (queue, move, remove, etc.)
    - config: Configuración (loop, autoplay, leave)
    - stats: Estadísticas (mystats, history, topsongs, etc.)
    - info: Información (nowplaying, lyrics, help)
    - wrapped: Comandos de Wrapped

    Uso:
        @commands.command(name="play")
        @command_category("playback")
        async def play(self, ctx, *, url: str):
            ...
    """
    def decorator(func):
        func.category = category
        return func
    return decorator
