"""
Planificateur de tâches Windows (schtasks).

** Contrats **
install prend hour: int<0-23>, minute: int<0-59>, password: str | None.
- password fourni : la tâche tourne même sans session ouverte (LogonType Password).
- password absent : la tâche ne tourne que si l'utilisateur est connecté (InteractiveToken).
"""
import getpass
import logging
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

from autobackup.scheduler.errors import SchedulerError

logger = logging.getLogger(__name__)


# - I - Construction de la tâche
TASK_NAME = "Autobackup"  # Nom de la tâche dans le Planificateur
_NS = "http://schemas.microsoft.com/windows/2004/02/mit/task"


def _account() -> str:
    """Compte sous lequel la tâche tourne : DOMAINE\\utilisateur (domaine = nom du PC en local)."""
    return f"{os.environ.get('USERDOMAIN', '')}\\{getpass.getuser()}".lstrip("\\")


def _next_start(hour: int, minute: int, now: datetime) -> datetime:
    """Prochaine occurrence de hour:minute : aujourd'hui si elle est à venir, sinon demain."""
    start = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return start if start > now else start + timedelta(days=1)


def build_task_xml(hour: int, minute: int, with_password: bool,
                   now: datetime | None = None) -> str:
    """XML de la tâche. Fonction pure : testable sans Windows."""
    if not (0 <= hour < 24 and 0 <= minute < 60):
        raise ValueError(f"Heure invalide : {hour:02d}:{minute:02d}")
    start = _next_start(hour, minute, now or datetime.now())

    ET.register_namespace("", _NS)
    q = lambda tag: f"{{{_NS}}}{tag}"  # noqa: E731  (nom qualifié par l'espace de noms)

    def sub(parent: ET.Element, tag: str, text: str | None = None) -> ET.Element:
        el = ET.SubElement(parent, q(tag))
        if text is not None:
            el.text = text
        return el

    task = ET.Element(q("Task"), version="1.2")

    info = sub(task, "RegistrationInfo")
    sub(info, "Description", "Backup quotidien (autobackup)")

    trigger = sub(sub(task, "Triggers"), "CalendarTrigger")
    sub(trigger, "StartBoundary", start.strftime("%Y-%m-%dT%H:%M:%S"))
    sub(trigger, "Enabled", "true")
    sub(sub(trigger, "ScheduleByDay"), "DaysInterval", "1")

    principal = sub(sub(task, "Principals"), "Principal")
    principal.set("id", "Author")
    sub(principal, "LogonType", "Password" if with_password else "InteractiveToken")
    sub(principal, "RunLevel", "LeastPrivilege")

    settings = sub(task, "Settings")
    sub(settings, "MultipleInstancesPolicy", "IgnoreNew")    # pas deux runs en parallèle
    sub(settings, "DisallowStartIfOnBatteries", "false")
    sub(settings, "StopIfGoingOnBatteries", "false")
    sub(settings, "StartWhenAvailable", "true")              # rattrape un run manqué
    sub(settings, "Enabled", "true")
    sub(settings, "ExecutionTimeLimit", "PT12H")             # arrête un run bloqué

    actions = sub(task, "Actions")
    actions.set("Context", "Author")
    exec_ = sub(actions, "Exec")
    sub(exec_, "Command", sys.executable)
    sub(exec_, "Arguments", "-m autobackup --run")

    return ET.tostring(task, encoding="unicode")


# - II - Appels à schtasks
def _schtasks(*args: str) -> subprocess.CompletedProcess:
    """Lance schtasks ; lève SchedulerError en cas d'échec."""
    try:
        return subprocess.run(["schtasks", *args], check=True,
                              capture_output=True, text=True, errors="replace")
    except subprocess.CalledProcessError as e:
        message = (e.stderr or e.stdout).strip()
        raise SchedulerError(f"schtasks {args[0]} a échoué : {message}") from e


def _check_runnable() -> None:
    """Vérifie que la commande de la tâche fonctionne hors du dossier du projet."""
    result = subprocess.run([sys.executable, "-c", "import autobackup"],
                            cwd=Path(sys.executable).anchor,   # racine du disque, ex. C:\
                            capture_output=True, text=True, errors="replace")
    if result.returncode != 0:
        raise SchedulerError(
            "Le paquet autobackup n'est pas importable depuis l'interpréteur "
            f"{sys.executable}. Installe-le dans le venv : pip install -e .\n"
            f"{result.stderr.strip()}")


# - III - FONCTIONS PUBLIQUES
def install(hour: int, minute: int, password: str | None = None) -> None:
    """Installe (ou remplace) la tâche quotidienne."""
    xml = build_task_xml(hour, minute, with_password=password is not None)
    _check_runnable()

    args = ["/Create", "/TN", TASK_NAME, "/F"]           # /F : remplace une tâche existante
    if password is not None:
        args += ["/RU", _account(), "/RP", password]

    with tempfile.TemporaryDirectory() as tmp:
        xml_path = Path(tmp) / "task.xml"
        # Le Planificateur exporte ses tâches en UTF-16 : c'est le format le plus sûr.
        xml_path.write_text('<?xml version="1.0" encoding="UTF-16"?>\n' + xml,
                            encoding="utf-16")
        _schtasks(*args, "/XML", str(xml_path))

    if password is None:
        logger.warning("Tâche installée sans mot de passe : elle ne tournera "
                       "que si l'utilisateur est connecté.")
    logger.info("Tâche Windows installée : backup quotidien à %02d:%02d", hour, minute)


def uninstall() -> None:
    """Supprime la tâche. Sans effet si elle n'existe pas."""
    if is_installed():
        _schtasks("/Delete", "/TN", TASK_NAME, "/F")
        logger.info("Tâche Windows supprimée")


def is_installed() -> bool:
    """La tâche existe-t-elle dans le Planificateur ?"""
    result = subprocess.run(["schtasks", "/Query", "/TN", TASK_NAME],
                            capture_output=True, text=True, errors="replace")
    return result.returncode == 0


def run_now() -> None:
    """Lance la tâche immédiatement, dans le contexte du Planificateur (pour tester)."""
    _schtasks("/Run", "/TN", TASK_NAME)