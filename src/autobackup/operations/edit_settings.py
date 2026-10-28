"""
Opérations pour modifier les paramètres de l'application.

- Ouvre le fichier settings.toml
"""
import logging
import sys, os, subprocess

from pathlib import Path

from autobackup.notify import new_topic
from autobackup.pairs import settings_filename
from autobackup.paths import config_dir


logger = logging.getLogger(__name__)


def open_file_settings() -> None:
    """Ouvre le fichier settings.toml dans l'éditeur par défaut du système.
    Raises:
        FileNotFoundError: si le fichier settings.toml n'existe pas.
    """
    settings_file = config_dir() / settings_filename()
    if not settings_file.exists():
        logger.debug("Settings file does not exist, value=%s.", settings_file)
        raise FileNotFoundError("%s does not exist.", settings_file)

    print("New random topic:", new_topic())

    open_in_editor(settings_file) 


def open_in_editor(path: Path) -> None:
    """Ouvre un fichier dans un éditeur de texte, selon l'OS.
    Args:
        path (Path): Le chemin vers le fichier à ouvrir.
    Raises:
        OSError: si l'ouverture échoue.
    """
    try:
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
    except FileNotFoundError as e:
        raise
    except OSError as e:
        logger.debug("Failed to open file %s in editor.", path)
        raise
