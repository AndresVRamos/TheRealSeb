"""
Verificador e instalador de actualizaciones — consulta GitHub Releases al iniciar el bot.
"""
import logging
import os
import subprocess
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

import aiohttp

from core.config import VERSION, GITHUB_REPO

_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def _parse_version(v: str) -> tuple:
    try:
        return tuple(int(x) for x in v.lstrip('v').split('.'))
    except ValueError:
        return (0,)


def _do_install(download_url: str, filename: str):
    """
    Descarga el instalador y lo ejecuta en modo silencioso.
    Corre en un thread separado para no bloquear nada.
    """
    dest = Path(tempfile.gettempdir()) / filename
    last_logged_pct = [-1]

    def _progress(count, block_size, total):
        if total <= 0:
            return
        pct = min(int(count * block_size / total * 100), 100)
        step = 20
        bucket = (pct // step) * step
        if bucket != last_logged_pct[0]:
            last_logged_pct[0] = bucket
            logging.info(f"[Updater] Descargando... {bucket}%")

    try:
        logging.info(f"[Updater] Iniciando descarga de {filename}...")
        urllib.request.urlretrieve(download_url, dest, reporthook=_progress)
        logging.info("[Updater] Descarga completa.")
    except Exception as e:
        logging.error(f"[Updater] Error al descargar el instalador: {e}")
        return

    logging.info("[Updater] Lanzando instalador silencioso en 3 segundos...")
    logging.info("[Updater] El bot se cerrará automáticamente para completar la actualización.")
    time.sleep(3)

    # /VERYSILENT   → sin UI
    # /SUPPRESSMSGBOXES → sin popups de error
    # /NORESTART    → no reiniciar Windows
    # /FORCECLOSEAPPLICATIONS → cerrar apps que bloqueen archivos
    # /TASKS=launchbot → lanzar el bot al terminar
    subprocess.Popen([
        str(dest),
        '/VERYSILENT',
        '/SUPPRESSMSGBOXES',
        '/NORESTART',
        '/FORCECLOSEAPPLICATIONS',
        '/TASKS=launchbot'
    ])

    # Dar tiempo al instalador para iniciar antes de cerrar
    time.sleep(5)
    os._exit(0)


def start_install(download_url: str, filename: str):
    """Dispara la descarga e instalación en un thread separado."""
    t = threading.Thread(target=_do_install, args=(download_url, filename), daemon=True)
    t.start()


async def check_for_updates(notify_fn=None):
    """
    Consulta la API de GitHub Releases y notifica si hay una versión más nueva.
    notify_fn: callable(version, release_url, download_url, filename)
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

        latest_tag     = data.get("tag_name", "")
        release_url    = data.get("html_url", f"https://github.com/{GITHUB_REPO}/releases")
        latest_version = latest_tag.lstrip('v')

        if _parse_version(latest_version) <= _parse_version(VERSION):
            logging.info(f"[Updater] Bot actualizado (v{VERSION})")
            return

        # Buscar el .exe entre los assets del release
        assets    = data.get("assets", [])
        exe_asset = next((a for a in assets if a["name"].endswith(".exe")), None)

        download_url = exe_asset["browser_download_url"] if exe_asset else None
        filename     = exe_asset["name"] if exe_asset else None

        logging.warning("=" * 60)
        logging.warning(f"  ACTUALIZACIÓN DISPONIBLE: v{latest_version}  (actual: v{VERSION})")
        if download_url:
            logging.warning("  Haz clic en 'Actualizar ahora' en el menú del tray.")
        else:
            logging.warning(f"  Descargá manualmente en: {release_url}")
        logging.warning("=" * 60)

        if notify_fn:
            notify_fn(latest_version, release_url, download_url, filename)

    except aiohttp.ClientError as e:
        logging.debug(f"[Updater] No se pudo verificar actualizaciones: {e}")
    except Exception as e:
        logging.debug(f"[Updater] Error inesperado al verificar actualizaciones: {e}")
