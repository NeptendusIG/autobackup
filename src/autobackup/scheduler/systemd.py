"""
Timer systemd utilisateur (Linux).

** Contrats **
install prend hour: int<0-23>, minute: int<0-59> ; password est ignoré (sans objet sous Linux).
Sans « linger » (loginctl enable-linger), la tâche ne tourne que si l'utilisateur a une session.
"""
import getpass
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

from autobackup.scheduler.errors import SchedulerError

logger = logging.getLogger(__name__)


# - I - Construction des unités
UNIT_NAME = "autobackup"  # → autobackup.service + autobackup.timer


def _unit_dir() -> Path:
    """Dossier des unités utilisateur (respecte XDG_CONFIG_HOME, comme systemd)."""
    config = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(config) / "systemd" / "user"


def _service_path() -> Path:
    return _unit_dir() / f"{UNIT_NAME}.service"


def _timer_path() -> Path:
    return _unit_dir() / f"{UNIT_NAME}.timer"


def _quote(arg: str, *, executable: bool = False) -> str:
    """Un argument d'ExecStart, selon les règles de systemd (ce n'est pas un shell).

    Entre guillemets doubles : \\ et " sont échappés, % (spécificateurs) est doublé.
    $ (variables) n'est doublé que dans les arguments : systemd ne développe pas
    les variables dans le chemin de l'exécutable, où $$ resterait littéralement $$.
    """
    escaped = arg.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%")
    if not executable:
        escaped = escaped.replace("$", "$$")
    return f'"{escaped}"'


def build_service() -> str:
    """Contenu de autobackup.service. Fonction pure : testable sans systemd."""
    args = " ".join(_quote(a) for a in ["-m", "autobackup", "--run"])
    command = f"{_quote(sys.executable, executable=True)} {args}"
    return (
        "[Unit]\n"
        "Description=Backup quotidien (autobackup)\n"
        "\n"
        "[Service]\n"
        "Type=oneshot\n"
        f"ExecStart={command}\n"
    )


def build_timer(hour: int, minute: int) -> str:
    """Contenu de autobackup.timer. Fonction pure : testable sans systemd."""
    if not (0 <= hour < 24 and 0 <= minute < 60):
        raise ValueError(f"Heure invalide : {hour:02d}:{minute:02d}")
    return (
        "[Unit]\n"
        "Description=Déclenchement quotidien d'autobackup\n"
        "\n"
        "[Timer]\n"
        f"OnCalendar=*-*-* {hour:02d}:{minute:02d}:00\n"
        "Persistent=true\n"          # rattrape un run manqué (machine éteinte)
        "\n"
        "[Install]\n"
        "WantedBy=timers.target\n"
    )


# - II - Appels à systemctl / loginctl
def _systemctl_available() -> bool:
    return shutil.which("systemctl") is not None


def _systemctl(*args: str) -> None:
    """Lance systemctl --user ; lève SchedulerError en cas d'échec."""
    if not _systemctl_available():
        raise SchedulerError("systemd n'est pas disponible sur ce système (systemctl absent).")
    try:
        subprocess.run(["systemctl", "--user", *args], check=True,
                       capture_output=True, text=True, errors="replace")
    except subprocess.CalledProcessError as e:
        message = (e.stderr or e.stdout).strip()
        raise SchedulerError(f"systemctl --user {args[0]} a échoué : {message}") from e


def _linger_enabled() -> bool:
    """L'utilisateur a-t-il le « linger » (tâches actives sans session ouverte) ?"""
    if shutil.which("loginctl") is None:
        return False
    result = subprocess.run(
        ["loginctl", "show-user", getpass.getuser(), "--property=Linger", "--value"],
        capture_output=True, text=True, errors="replace")
    return result.returncode == 0 and result.stdout.strip() == "yes"


def _check_runnable() -> None:
    """Vérifie que la commande de la tâche fonctionne hors du dossier du projet."""
    result = subprocess.run([sys.executable, "-c", "import autobackup"],
                            cwd="/", capture_output=True, text=True, errors="replace")
    if result.returncode != 0:
        raise SchedulerError(
            "Le paquet autobackup n'est pas importable depuis l'interpréteur "
            f"{sys.executable}. Installe-le dans le venv : pip install -e .\n"
            f"{result.stderr.strip()}")


# - III - FONCTIONS PUBLIQUES
def install(hour: int, minute: int, password: str | None = None) -> None:
    """Installe (ou remplace) le timer quotidien. `password` est ignoré sous Linux."""
    service, timer = build_service(), build_timer(hour, minute)
    if not _systemctl_available():
        raise SchedulerError("systemd n'est pas disponible sur ce système (systemctl absent).")
    _check_runnable()

    _unit_dir().mkdir(parents=True, exist_ok=True)
    _service_path().write_text(service, encoding="utf-8")
    _timer_path().write_text(timer, encoding="utf-8")

    _systemctl("daemon-reload")                       # relire les fichiers modifiés
    _systemctl("enable", "--now", f"{UNIT_NAME}.timer")
    _systemctl("restart", f"{UNIT_NAME}.timer")       # appliquer une nouvelle heure si déjà actif

    if not _linger_enabled():
        logger.warning("Linger désactivé : le timer ne tournera que si une session est ouverte. "
                       "Pour l'activer : loginctl enable-linger %s", getpass.getuser())
    logger.info("Timer systemd installé : backup quotidien à %02d:%02d", hour, minute)


def uninstall() -> None:
    """Désactive le timer et supprime les unités. Sans effet si rien n'est installé."""
    had_files = _service_path().exists() or _timer_path().exists()
    if is_installed():
        _systemctl("disable", "--now", f"{UNIT_NAME}.timer")
        logger.info("Timer systemd désactivé")
    _timer_path().unlink(missing_ok=True)
    _service_path().unlink(missing_ok=True)
    if had_files and _systemctl_available():
        _systemctl("daemon-reload")


def is_installed() -> bool:
    """Le timer est-il activé ?"""
    if not _systemctl_available():
        return False
    result = subprocess.run(["systemctl", "--user", "is-enabled", f"{UNIT_NAME}.timer"],
                            capture_output=True, text=True, errors="replace")
    return result.returncode == 0


def run_now() -> None:
    """Lance le backup immédiatement, dans le contexte de systemd (pour tester).

    --no-block : rend la main tout de suite ; suivre le run avec
    journalctl --user -u autobackup.service
    """
    _systemctl("start", "--no-block", f"{UNIT_NAME}.service")