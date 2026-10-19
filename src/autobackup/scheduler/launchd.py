"""
Launchd implementation for macOS.

** Contrats **
install prends hour: int<0-23>, minute: int<0-59>; [faits...]
"""
import logging
import os
import sys
import plistlib
import subprocess

from pathlib import Path

from autobackup.paths import log_dir


logger = logging.getLogger(__name__)


# - I - Fonctions pour créer la tâche planifiée
LABEL = "be.gaetan.autobackup"  # Nom du job pour launchd
LAUNCH_AGENTS_PATH = Path.home() / "Library" / "LaunchAgents"


def _plist_path() -> Path:
    """Renvoie le chemin du fichier .plist pour launchd."""
    return LAUNCH_AGENTS_PATH / f"{LABEL}.plist"


def _domain() -> str:
    """Renvoie le domaine pour launchctl (contexte utilisateur)."""
    return f"gui/{os.getuid()}"


def build_job(hour: int, minute: int, logs: Path) -> dict:
    """Crée un dictionnaire représentant le job pour launchd."""
    return {
        "Label": LABEL,  # .daily",
        "ProgramArguments": [sys.executable, "-m", "autobackup", "--run"],
        "StartCalendarInterval": {"Hour": hour, "Minute": minute},
        "StandardOutPath": str(logs / "launchd.out.log"),
        "StandardErrorPath": str(logs / "launchd.err.log"),
    }


def _write_files(job: dict) -> None:
    """Écrit le fichier .plist dans ~/Library/LaunchAgents."""
    if not LAUNCH_AGENTS_PATH.exists():
        logger.info(f"LaunchAgents directory does not exist: {LAUNCH_AGENTS_PATH}")
        LAUNCH_AGENTS_PATH.mkdir(parents=True, exist_ok=True)

    plist_path = _plist_path()
    with open(plist_path, "wb") as f:
        plistlib.dump(job, f)
    logger.info(f"Launchd job written to {plist_path}")


# - II - FONCTIONS PUBLIQUES
def install(hour: int, minute: int) -> None:
    """Installe le planificateur de tâches pour exécuter le backup automatiquement.
    @REQUIRE : launchd (macOS) 
                hour: int<0-23>, minute: int<0-59>
    """
    if is_installed():
        logger.info("An existing launchd job is already installed. Uninstalling it first.")
        uninstall()  # Supprime l'ancien job s'il existe sinon error

    # 1 - Créer le fichier de configuration du launchd
    job = build_job(hour, minute, log_dir())
    _write_files(job)

    # 2 - Charger le fichier de configuration avec launchctl
    try:
        subprocess.run(["launchctl", "bootstrap", _domain(), str(_plist_path())], 
                       check=True, capture_output=True, text=True)
        logger.info("Launchd job installed and loaded successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to load launchd job: {e.stderr}")
        raise RuntimeError(f"Failed to load launchd job: {e.stderr}") from e
    logger.info(f"Backup scheduled at {hour:02d}:{minute:02d} daily.")


def uninstall() -> None:
    """Désinstalle le planificateur de tâches."""
    # Retirer la tâche planifiée
    if not is_installed():
        logger.info("No launchd job is currently installed.")
        return
    
    try:
        subprocess.run(["launchctl", "bootout", _domain(), str(_plist_path())], 
                       check=True, capture_output=True, text=True)
        logger.info("Launchd job unloaded successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to unload launchd job: {e.stderr}")
        raise RuntimeError(f"Failed to unload launchd job: {e.stderr}") from e

    # Supprimer le fichier .plist
    _plist_path().unlink(missing_ok=True)
    logger.info("Launchd job file removed successfully.")


def is_installed() -> bool:
    """Vérifie si le planificateur de tâches est installé."""
    try:
        result = subprocess.run(["launchctl", "print", f"{_domain()}/{LABEL}"],
                                capture_output=True, text=True)
        return result.returncode == 0
    except subprocess.CalledProcessError:
        return False

