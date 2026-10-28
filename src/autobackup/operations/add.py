"""
Opération d'ajouter une nouvelle paire de backup.
"""
import logging
import questionary as q

from pathlib import Path
from autobackup.pairs import Pair, read_pairs, write_pairs
from autobackup.paths import config_dir
from autobackup.file_explorer import ask_dir


logger = logging.getLogger(__name__)


def manage_add_pair() -> None:
    """Ajoute une nouvelle paire de backup.
    Raises:
        from read_pairs, write_pairs:
            OSError: si une erreur de lecture/écriture du fichier pairs.toml se produit.
            ConfigError: si le fichier pairs.toml est mal formé.
    """

    # - 1 - Demander à l'utilisateur les chemins source et destination
    source = _ask_directory("Select source directory")
    if source is None:
        logger.info("Source directory selection cancelled.")
        return

    destination = _ask_directory("Select destination directory")
    if destination is None:
        logger.info("Destination directory selection cancelled.")
        return

    if source.is_relative_to(destination) or destination.is_relative_to(source):
        logger.error("Source and destination paths cannot be nested within each other.")
        logger.error("Add operation aborted. Source: %s, Destination: %s", source, destination)
        return

    # - 2 - Créer la nouvelle paire
    new_pair = Pair(source=source, destination=destination)

    # - 3 - Lire la liste actuelle, ajouter la nouvelle paire et sauvegarder
    pairs = read_pairs(config_dir())  
    pairs.append(new_pair)
    write_pairs(config_dir(), pairs)
    logger.info("Paire ajoutée : %s → %s", source, destination)
    q.print("Paire ajoutée.", style="fg:green")



def _validate_dir(path: str) -> bool|str:
    """Valide que le chemin est un dossier existant."""
    p = Path(path)
    if not p.exists():
        return "Le chemin n'existe pas."
    if not p.is_dir():
        return "Le chemin n'est pas un dossier."
    return True


def _normalize(path: Path) -> Path:
    """Normalise le chemin pour éviter les doublons."""
    return path.expanduser().resolve()  


def _ask_directory(label: str) -> Path | None:
    """Sélecteur graphique si possible, sinon saisie au terminal."""
    try:
        chosen = ask_dir(title=label)
    except RuntimeError as e:
        logger.debug("Sélecteur graphique indisponible : %s", e)
        chosen = Path(q.path(f"{label} :", only_directories=True,
                             validate=_validate_dir).unsafe_ask())
    return _normalize(chosen) if chosen is not None else None
