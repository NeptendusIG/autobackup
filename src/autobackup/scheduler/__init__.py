# scheduler/__init__.py
"""__init__.py
Interface publique de autobackup.scheduler : fonctions pour la planification de tâches.
    -> Quel que soit l'OS.
"""

import sys
from types import ModuleType

from autobackup.scheduler.errors import SchedulerError

# Fonction de Dispatch
def _backend() -> ModuleType:
    """Renvoie le module qui implémente la planification pour l'OS courant."""
    if sys.platform == "win32":
        from autobackup.scheduler import windows as backend
    elif sys.platform == "darwin":
        from autobackup.scheduler import launchd as backend
    elif sys.platform.startswith("linux"):
        #from autobackup.scheduler import systemd as backend
        raise NotImplementedError("Scheduler for Linux is not implemented yet (and won't be).") 
    else:
        raise NotImplementedError(f"OS non supporté : {sys.platform}")
    return backend


def install(hour: int, minute: int) -> None:
    _backend().install(hour, minute)


def uninstall() -> None:
    _backend().uninstall()


def is_installed() -> bool:
    return _backend().is_installed()