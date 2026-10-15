"""
** Configuration du logging. **
Ce module établit uniquement la configuration (via setup_logging()).
Les autres modules font :

    import logging
    log = logging.getLogger(__name__)

"""
import logging, sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from types import TracebackType


LOGGER_NAME = "autobackup"
LOG_FILENAME = "autobackup.log"
MAX_BYTES = 1_000_000
BACKUP_COUNT = 5  # pour rotation autobackup.log.1, ..., autobackup.log.5 

FILE_FORMAT = "%(asctime)s - %(levelname)-8s : %(name)s | %(message)s"
CONSOLE_FORMAT = "%(levelname)-8s : %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _log_uncaught_exception(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_tb: TracebackType | None,
) -> None:
    """Écrit une exception non rattrapée dans le log, avec sa trace complète."""
    # Un Ctrl+C n'est pas un plantage : on laisse Python le traiter normalement.
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
 
    # exc_info joint la trace complète au message. Elle part dans le fichier
    # ET sur la console, via les handlers ; c'est pourquoi on n'appelle pas
    # aussi le hook par défaut, qui l'afficherait une seconde fois.
    logging.getLogger(LOGGER_NAME).critical(
        "Exception non rattrapée",
        exc_info=(exc_type, exc_value, exc_tb),
    )


def setup_logging(log_dir: Path, *, verbose: bool = False) -> Path:
    """Configure le logger 'autobackup'. Renvoie le chemin du fichier de log.

        - Fichier : tout à partir de INFO (DEBUG si verbose), avec rotation (1 Mo x 5).
        - Console : tout à partir de WARNING (DEBUG si verbose).
        - Exceptions : Les exceptions non interceptées sont loggées automatiquement (via sys.excepthook).

        Idempotent : peut être appelée plusieurs fois, les handlers précédents sont remplacés.
    """
    logger = logging.getLogger(LOGGER_NAME)

    # (Idempotence) Supprimer les handlers existants
    #for handler in list(logger.handlers):
    #    logger.removeHandler(handler)
    #    handler.close()

    # Assurer que le répertoire de log existe
    #log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / LOG_FILENAME

    # Poser le filtre général
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Pas de propagation vers le logger racine (pour éviter les doublons)
    #logger.propagate = False

    # Configurer le filehandler
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(FILE_FORMAT, datefmt=DATE_FORMAT))
    logger.addHandler(file_handler)

    # Configurer le consolehandler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.DEBUG if verbose else logging.WARNING)
    console_handler.setFormatter(logging.Formatter(CONSOLE_FORMAT))
    logger.addHandler(console_handler)

    # Logger les exceptions non interceptées
    sys.excepthook = _log_uncaught_exception

    return log_file


