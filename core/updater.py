"""
Verificador de actualizaciones — consulta GitHub Releases al iniciar el bot.
"""
import aiohttp
import logging

from core.config import VERSION, GITHUB_REPO

_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def _parse_version(v: str) -> tuple:
    try:
        return tuple(int(x) for x in v.lstrip('v').split('.'))
    except ValueError:
        return (0,)


async def check_for_updates(notify_fn=None):
    """
    Consulta la API de GitHub Releases y notifica si hay una versión más nueva.
    notify_fn: callable(version, url) para mostrar notificación en el system tray.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                _API_URL,
                headers={"Accept": "application/vnd.github+json"},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    logging.debug(f"[Updater] GitHub API respondió {resp.status}, omitiendo check.")
                    return
                data = await resp.json()

        latest_tag = data.get("tag_name", "")
        release_url = data.get("html_url", f"https://github.com/{GITHUB_REPO}/releases")
        latest_version = latest_tag.lstrip('v')

        if _parse_version(latest_version) > _parse_version(VERSION):
            logging.warning("=" * 60)
            logging.warning(f"  ACTUALIZACIÓN DISPONIBLE: v{latest_version}  (actual: v{VERSION})")
            logging.warning(f"  Descargá el instalador en:")
            logging.warning(f"  {release_url}")
            logging.warning("=" * 60)

            if notify_fn:
                notify_fn(latest_version, release_url)
        else:
            logging.info(f"[Updater] Bot actualizado (v{VERSION})")

    except aiohttp.ClientError as e:
        logging.debug(f"[Updater] No se pudo verificar actualizaciones: {e}")
    except Exception as e:
        logging.debug(f"[Updater] Error inesperado: {e}")
