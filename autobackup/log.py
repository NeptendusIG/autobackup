"""
Configuration du logging.

Les modules ne configurent jamais le logging : ils font seulement
`log = logging.getLogger(__name__)`. Seul le point d'entrée (CLI ou daemon)
appelle `setup()`.

- stdout : réservé au résultat du programme (`print`).
- stderr : logs de la console (diagnostic).
- fichier : logs du daemon, avec rotation.

Ne jamais logger le texte lu par l'utilisateur, seulement des métadonnées
(bundle id, compteurs, durées).
"""
import logging
import logging.handlers
import os
import sys
from pathlib import Path

ROOT_LOGGER = "autobackup"
ENV_LEVEL = "AUTOBACKUP_LOG"  # ex: AUTOBACKUP_LOG=debug

LOG_DIR = Path.home() / "Library" / "Logs" / "autobackup"
DAEMON_LOG = LOG_DIR / "daemon.log"

LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
MAX_BYTES = 1_000_000
BACKUP_COUNT = 3


# ------------------------------------
# ------------------------------------


def _parse_level(value):
    """Convertit 'debug', 'INFO', 10... en niveau logging. None si invalide."""
    if isinstance(value, int):
        return value
    return LEVELS.get(str(value).strip().upper())


def setup(*, level="WARNING", file=None, console=True):
    """
    Configure le logger racine `autobackup`. Peut être appelée plusieurs fois :
    les handlers posés par un appel précédent sont remplacés.

    - level   : niveau par défaut. La variable ASSISTANT_LOG, si valide, prime.
    - file    : chemin d'un fichier de log (rotation 1 Mo x 3), ou None.
    - console : écrit aussi sur stderr.
    """
    resolved = _parse_level(os.environ.get(ENV_LEVEL, "")) or _parse_level(level) or logging.WARNING

    root = logging.getLogger(ROOT_LOGGER)
    root.setLevel(resolved)

    for handler in [h for h in root.handlers if getattr(h, "_autobackup", False)]:
        root.removeHandler(handler)
        handler.close()

    formatter = logging.Formatter(FORMAT)
    handlers = []

    if console:
        handlers.append(logging.StreamHandler(sys.stderr))
    if file is not None:
        file = Path(file)
        file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.handlers.RotatingFileHandler(
            file, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
        ))

    for handler in handlers:
        handler.setFormatter(formatter)
        handler._autobackup = True
        root.addHandler(handler)

    return root


def setup_cli(*, verbose=0):
    """CLI : WARNING sur stderr, INFO avec -v, DEBUG avec -vv. Pas de fichier."""
    return setup(level=("WARNING", "INFO", "DEBUG")[min(int(verbose), 2)])


def setup_daemon(*, foreground=False, file=DAEMON_LOG):
    """Daemon : INFO dans le fichier. Console en plus au premier plan."""
    root = setup(level="INFO", file=file, console=foreground)
    sys.excepthook = _log_uncaught
    return root


def _log_uncaught(exc_type, exc, tb):
    """Trace les exceptions non gérées, sinon elles disparaissent sous launchd."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc, tb)
        return
    logging.getLogger(ROOT_LOGGER).critical("exception non gérée", exc_info=(exc_type, exc, tb))
