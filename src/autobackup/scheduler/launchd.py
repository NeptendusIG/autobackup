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
        LAUNCH_AGENTS_PATH.mkdir(parents=True, exist_ok=True)
        logger.info("LaunchAgents directory created at %s", LAUNCH_AGENTS_PATH)

    plist_path = _plist_path()
    with open(plist_path, "wb") as f:
        plistlib.dump(job, f)
    logger.debug("Launchd job written to %s", plist_path)


# - II - FONCTIONS PUBLIQUES
def install(hour: int, minute: int) -> None:
    """Installe le planificateur de tâches pour exécuter le backup automatiquement.
    Args: 
        hour: int<0-23>
        minute: int<0-59>
    Require : launchd (macOS) 
                hour: int<0-23>, minute: int<0-59>
    Result : 
        crée le fichier .plist (tâche planifiée)
        installe la tâche planifiée (activation)
        la tâche est l'appel de `python -m autobackup --run` à l'heure planifiée
    Raises:
        RuntimeError: si l'installation échoue.
    """
    if is_installed():
        logger.debug("An existing launchd job is already installed. Uninstalling it first...")
        uninstall()  # Supprime l'ancien job s'il existe sinon error
        logger.info("Previous launchd job uninstalled successfully.")

    # 1 - Créer le fichier de configuration du launchd
    job = build_job(hour, minute, log_dir())
    _write_files(job)
    logger.info("Launchd job file created at %s", _plist_path())

    # 2 - Charger le fichier de configuration avec launchctl
    command = ["launchctl", "bootstrap", _domain(), str(_plist_path())]
    logger.debug("Executing launchctl command: %s", " ".join(command))

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        logger.info("Launchd command to install and load the job executed successfully.")
    except subprocess.CalledProcessError as e:
        logger.debug("Failed to load launchd job: %s", e.stderr)
        raise RuntimeError("Failed to load launchd job: %s", e.stderr) from e
    logger.debug("Backup scheduled at %02d:%02d daily.", hour, minute)


def uninstall() -> None:
    """Désinstalle le planificateur de tâches."""
    # Retirer la tâche planifiée
    if not is_installed():
        logger.info("No launchd job is currently installed.")
        return
    command = ["launchctl", "bootout", _domain(), str(_plist_path())]
    logger.debug("Executing launchctl command: %s", " ".join(command))

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        logger.info("Launchd job unloaded successfully.")
    except subprocess.CalledProcessError as e:
        logger.debug("Failed to unload launchd job: %s", e.stderr)
        raise RuntimeError("Failed to unload launchd job: %s", e.stderr) from e

    # Supprimer le fichier .plist
    _plist_path().unlink(missing_ok=True)
    logger.debug("Launchd job file removed successfully.")


def is_installed() -> bool:
    """Vérifie si le planificateur de tâches est installé."""
    command = ["launchctl", "print", f"{_domain()}/{LABEL}"]
    logger.debug("Executing launchctl command: %s", " ".join(command))

    try:
        result = subprocess.run(command, capture_output=True, text=True)
        return result.returncode == 0
    except subprocess.CalledProcessError:
        return False

