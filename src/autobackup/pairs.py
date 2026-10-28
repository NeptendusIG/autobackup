"""
Lecture et écriture en TOML.

Fixé dans ce module :
- Paires de répertoires à sauvegarder : pairs.toml
- Paramètres de configuration : settings.toml

Fonctions disponibles :
    - ensure_files(config_dir: Path) -> None
    - read_pairs(config_dir: Path) -> list[Pair]
    - write_pairs(config_dir: Path, pairs: list[Pair]) -> None
    - read_settings(config_dir: Path) -> Settings
    - write_settings(config_dir: Path, settings: Settings) -> None

Classes de données :
    - Pair
    - Settings
"""

import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
import tomllib  # pour lire TOML en dict
import tomli_w  # pour écrire dict en TOML

from autobackup.error import ConfigError

logger = logging.getLogger(__name__)



_PAIRS_FILENAME = "pairs.toml"
_SETTINGS_FILENAME = "settings.toml"
_DEFAULT_HOUR = "00:00"

def settings_filename() -> str:
    """Renvoie le nom du fichier de configuration des paramètres."""
    return _SETTINGS_FILENAME

def pairs_filename() -> str:
    """Renvoie le nom du fichier de configuration des paires de backup."""
    return _PAIRS_FILENAME

def default_hour_setting() -> str:
    """Renvoie l'heure par défaut pour le backup."""
    return _DEFAULT_HOUR

def default_hour() -> tuple[int, int]:
    """Renvoie l'heure par défaut pour le backup sous forme de tuple (heure, minute)."""
    h, m = _DEFAULT_HOUR.split(":")
    return int(h), int(m)


@dataclass
class Pair:
    source: Path
    destination: Path 

@dataclass
class Settings:
    sender_email: str = ""       # Il faut vérifier que le champ a été rempli à chaque lecture
    sender_email_key: str = field(default="", repr=False)   # Il faut vérifier que le champ a été rempli à chaque lecture
    receivers_emails: list[str] = field(default_factory=list)
    ntfy_server: str = "https://ntfy.sh"  # serveur public par défaut
    ntfy_topic: str = ""
    hour: str = _DEFAULT_HOUR  # heure par défaut


# - 1 - Créer les fichiers toml

def ensure_files(config_dir: Path) -> None:
    """Crée pairs.toml et settings.toml avec leur contenu par défaut s'ils sont absents.

    Raises:
        OSError: si un fichier ne peut pas être créé.
    """
    pairs_file = config_dir / _PAIRS_FILENAME
    settings_file = config_dir / _SETTINGS_FILENAME

    # Premier lancement : aucun des deux fichiers n'existe. Sinon, un fichier manquant est anormal.
    first_run = not pairs_file.exists() and not settings_file.exists()
    level = logging.INFO if first_run else logging.WARNING

    if not pairs_file.exists():
        write_pairs(config_dir, [])
        logger.log(level, "Fichier de paires absent, créé vide : %s", pairs_file)

    if not settings_file.exists():
        write_settings(config_dir, Settings())
        logger.log(level, "Fichier de réglages absent, créé avec les valeurs par défaut : %s", settings_file)


# - 2 - Lire et écrire dans le fichier des PAIRS de backup

def read_pairs(config_dir: Path) -> list[Pair]:
    """Lit le fichier TOML et renvoie la liste des paires.
    Args: 
        config_dir: Path du dossier de configuration
    Returns:
        Liste de Pair lue dans le fichier TOML
    Raises:
        OSError (FileNotFoundError, Chemin trop long, réseau déconnecté)
        ConfigError si le fichier est mal formé (mauvais format d'une paire).
    """
    file_path = config_dir / _PAIRS_FILENAME
    try:
        with open(file_path, "rb") as f:
            data = tomllib.load(f)
    except FileNotFoundError:
        logger.debug("[FileNotFoundError] Error reading pairs: file not found (%s)" % file_path)
        raise
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"Error decoding TOML file {file_path}") from e
    except UnicodeDecodeError as e:
        raise ConfigError(f"Error decoding TOML file {file_path}") from e
    logger.debug(f"Data have been read from {file_path}: {data.keys()}")

    # Parsing en Pair
    pairs = []
    for item in data.get("pairs", []):
        try:
            pair = Pair(Path(item["source"]), Path(item["destination"]))
            pairs.append(pair)
        except TypeError as e:
            logger.debug(f"[TypeError] Lors de la lecture d'une paire : {e}. Données : {item}")
            raise ConfigError(f"Invalid pair data.") from e
        except KeyError as e:
            raise ConfigError(f"[KeyError] Clé manquante lors de la lecture de la paire {item}")
    logger.debug(f"Processed {len(pairs)} pairs from {file_path}")
    return pairs


def write_pairs(config_dir: Path, pairs: list[Pair]) -> None:
    """Écrit la liste des paires dans le fichier TOML.
    Args: 
        config_dir: Path du dossier de configuration
        pairs: liste de Pair à écrire dans le fichier TOML
    Raises:  (seuls possibles si le contrat est respecté, sinon c'est un bug)
        OSError (FileNotFoundError, Chemin trop long, réseau déconnecté, disque plein)
    """
    #AttributeError si une paire est invalide  -> Pas besoin car rupture de contrat
    #TypeError si une valeur n'est pas serialisable en TOML (ex: Path) -> Pas besoin car on convertit en str
    #KeyboardInterrupt si l'utilisateur interrompt l'écriture (Ctrl+C) -> Pas besoin car l'interruption est toujours possible
    file_path = config_dir / _PAIRS_FILENAME

    data = {"pairs": [
        {"source": str(pair.source), "destination": str(pair.destination)}
        for pair in pairs]}

    content = tomli_w.dumps(data)

    with open(file_path, "wb") as f:
        f.write(content.encode("utf-8"))
    logger.debug(f"Wrote {len(pairs)} pairs to {file_path}")


# - 3 - Lire et écrire dans le fichier des SETTINGS de configuration

def read_settings(config_dir: Path) -> Settings:
    """Lit le fichier TOML et renvoie les paramètres de configuration.
    Args:
        config_dir: Path du dossier de configuration
    Returns:
        Settings : paramètres de configuration lus dans le fichier TOML
    Raises:
        OSError (FileNotFoundError, Chemin trop long, réseau déconnecté, disque plein)
        ConfigError si le fichier est mal formé (mauvais format d'une paire).
    """
    file_path = config_dir / _SETTINGS_FILENAME
    try:
        with open(file_path, "rb") as f:
            data = tomllib.load(f)
    except FileNotFoundError as e:
        logger.debug(f"[FileNotFoundError] Error reading settings: file not found ({file_path})")
        raise
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"Error decoding TOML file {file_path}") from e

    try:
        return Settings(**data.get("settings", {}))
    except TypeError as e:
        logger.debug(f"[TypeError] Lors de la lecture des paramètres : {e}. Données : {data.get('settings', {})}")
        raise ConfigError(f"Invalid settings data.") from e


def write_settings(config_dir: Path, settings: Settings) -> None:
    """Écrit les paramètres de configuration dans le fichier TOML.
    Args:
        config_dir: Path du dossier de configuration
        settings: Settings à écrire dans le fichier TOML
    Raises:
        OSError (FileNotFoundError, Chemin trop long, réseau déconnecté, disque plein)
    """
    file_path = config_dir / _SETTINGS_FILENAME
    data = {
        "settings": asdict(settings)
    }
    try:
        with open(file_path, "wb") as f:
            tomli_w.dump(data, f)
    except FileNotFoundError as e:
        logger.debug(f"[FileNotFoundError] Pour écrire les paramètres ({file_path})")
        raise
    except OSError as e:
        logger.debug(f"[OSError] Pour écrire les paramètres ({file_path}) : {e}")
        raise


def read_valid_hour(config_dir: Path) -> tuple[int, int]:
    """Lit le fichier settings.toml et renvoie l'heure de backup.
    Args:
        config_dir: Path du dossier de configuration
    Returns:
        Tuple[int, int] : (heure, minute) de backup
    Raises:
        ValueError si l'heure est mal formée ou hors limites.
    """
    settings = read_settings(config_dir)
    hour = settings.hour
    if not isinstance(hour, str) or len(hour) != 5 or hour[2] != ":":
        logger.debug("[ValueError] Invalid hour format=%s (expected HH:MM)", hour)
        raise ValueError("Invalid hour format=%s (expected HH:MM).", hour)
    h, m = hour.split(":")
    if not (h.isdigit() and m.isdigit() and 0 <= int(h) < 24 and 0 <= int(m) < 60):
        logger.debug("[ValueError] Invalid hour=%s.", hour)
        raise ValueError("Invalid hour=%s (number hour < 24, number minute < 60).", hour)
    return int(h), int(m)