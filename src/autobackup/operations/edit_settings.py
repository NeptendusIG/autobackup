"""
Opérations pour modifier les paramètres de l'application.

- Ouvre le fichier settings.toml
"""
import logging
import sys, os, subprocess

from pathlib import Path

from autobackup.pairs import __SETTINGS_FILENAME
from autobackup.paths import config_dir


logger = logging.getLogger(__name__)


def open_file_settings() -> None:
    """Ouvre le fichier settings.toml dans l'éditeur par défaut du système.
    """
    settings_file = config_dir() / __SETTINGS_FILENAME
    if not settings_file.exists():
        logger.error(f"Settings file {settings_file} does not exist.")
        raise FileNotFoundError(f"Settings file {settings_file} does not exist.")

    open_in_editor(settings_file) 


def open_in_editor(path: Path) -> None:
    """Ouvre un fichier dans un éditeur de texte, selon l'OS."""
    if sys.platform == "win32":
        subprocess.run(["notepad", str(path)])          # bloque jusqu'à la fermeture
    elif sys.platform == "darwin":
        subprocess.run(["open", "-t", str(path)])       # -t : éditeur de texte par défaut
    else:
        editor = os.environ.get("EDITOR")
        if editor:
            subprocess.run([editor, str(path)])         # nano, vim… dans le terminal
        else:
            subprocess.run(["xdg-open", str(path)])