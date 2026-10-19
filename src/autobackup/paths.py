"""
Fournit les emplacements standards.
"""

from platformdirs import PlatformDirs
from pathlib import Path

APPLICATION_NAME = "autobackup"

_dirs = PlatformDirs(APPLICATION_NAME, appauthor=False)

def config_dir() -> Path:
    return _dirs.user_config_path

def log_dir() -> Path:
    return _dirs.user_log_path  # ex: ~/Library/Logs/autobackup (macOS), ~/.local/share/autobackup/logs (Linux)

#def lock_file() -> Path:
#    return _dirs.user_state_path / "backup.lock"

def ensure_environment():
    """
    Crée les répertoires nécessaires si ils n'existent pas.
    """
    _dirs.user_config_path.mkdir(parents=True, exist_ok=True)
    _dirs.user_log_path.mkdir(parents=True, exist_ok=True)
    #_dirs.user_state_path.mkdir(parents=True, exist_ok=True)