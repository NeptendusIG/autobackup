"""
Faire le backup de toutes les paires.

** Améliorations Futures (ordre de priorité) **
1. Ajouter une lecture/gestion de la taille des fichiers et de l'espace disque disponible
2. Gérer parfaitement les exceptions (FileNotFoundError, FileExistsError, PermissionError, IsADirectoryError, NotADirectoryError)
3. Produire un rapport de backup (fichiers copiés, erreurs, etc.)
4. Suivre la taille et date de modification pour éviter de copier des fichiers non modifiés
5. Mettre un verrou pour ne pas lancer plusieurs backups en même temps (threading.Lock ou file lock)

** Edge Cases à gérer **
- pairs n'existe pas ?
- pairs est vide ? Ok
- dossier source pas trouvé ?
- dossier destination pas trouvé ?
- erreurs...
"""
import logging
import shutil
from pathlib import Path
from datetime import datetime

from autobackup.pairs import read_pairs
from autobackup.paths import config_dir
from autobackup.backup_results import BackupResult


logger = logging.getLogger(__name__)


TIME_FORMAT = "%Y-%m-%d_%H-%M-%S"
PREFIX_INCOMPLETE = "incomplete-"


def safe_copy_dir(source: Path, backup_dir: Path) -> bool:
    """Copie le contenu du dossier source vers le dossier destination.
    """
    if not source.exists() or not source.is_dir():
        logger.error(f"Source directory {source} does not exist or is not a directory.")
        raise FileNotFoundError(f"Source directory {source} does not exist or is not a directory.")

    if not backup_dir.exists():
        logger.error(f"Destination directory {backup_dir} does not exist or is not a directory.")
        raise FileNotFoundError(f"Destination directory {backup_dir} does not exist or is not a directory.")

    BACKUP_SUCCESS = True
    for item in source.iterdir():
        dest_item = backup_dir / item.name
        try:
            if item.is_dir():
                shutil.copytree(item, dest_item, dirs_exist_ok=True)
                logger.debug(f"Copied directory {item} to {dest_item}.")
            else:
                shutil.copy2(item, dest_item)
                logger.debug(f"Copied file {item} to {dest_item}.")
        except Exception as e:
            logger.error(f"Failed to copy {item} to {dest_item}: {e}")
            raise
        finally:
            if not dest_item.exists():
                logger.error(f"Failed to copy {item} to {dest_item}.")
                BACKUP_SUCCESS = False

    return BACKUP_SUCCESS

def create_directory(destination: Path, prefix: str = "") -> Path:
    """Création du dossier qui accueille le nouveau backup (timestamp et number).
    """
    backup_dir = destination / str(prefix + datetime.now().strftime(TIME_FORMAT))
    n = 1
    while backup_dir.exists() and n < 10:
        backup_dir = destination / str(prefix + datetime.now().strftime(TIME_FORMAT) + f"_{n}")
        n += 1
    if backup_dir.exists():
        logger.error(f"Failed to create a unique backup directory in {destination}.")
        raise FileExistsError(f"Failed to create a unique backup directory in {destination}.")
    backup_dir.mkdir(parents=False, exist_ok=False)
    logger.info(f"Created backup directory {backup_dir}.")
    return backup_dir


def run_backup() -> list[BackupResult]:
    """Exécute le backup pour toutes les paires définies dans pairs.toml.
    """
    pairs = read_pairs(config_dir())
    if not pairs:
        logger.warning("No backup pairs found. Please add a pair first.")
        print("No backup pairs found. Please add a pair first.")
        return []

    results: list[BackupResult] = []
    for pair in pairs:
        logger.info(f"Backing up from {pair.source} to {pair.destination}.")
        try:
            backup_dir: Path = create_directory(pair.destination, prefix=PREFIX_INCOMPLETE)
            backup_success: bool = safe_copy_dir(pair.source, backup_dir)
            if backup_success:
                # Rename the directory to remove the "incomplete" prefix
                final_backup_dir = pair.destination / backup_dir.name.replace(PREFIX_INCOMPLETE, "")
                backup_dir.rename(final_backup_dir)
                logger.info(f"Backup completed successfully for {pair.source} -> {final_backup_dir}.")
                results.append(BackupResult(source=str(pair.source), success=True, snapshot=final_backup_dir.name))
            else:
                logger.warning(f"Backup failed for {pair.source} -> {backup_dir}.")
                print(f"Backup failed for {pair.source} -> {backup_dir}.")
                results.append(BackupResult(source=str(pair.source), success=False, snapshot=backup_dir.name))
        except OSError as e:
            #except FileNotFoundError | FileExistsError | PermissionError | IsADirectoryError | NotADirectoryError as e:
            logger.error("Erreur lors du backup %s → %s : %s", pair.source, pair.destination, e)
            results.append(BackupResult(source=str(pair.source), destination=str(pair.destination), success=False, snapshot="", error="Error: " + str(e)))

    return results