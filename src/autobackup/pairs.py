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


logger = logging.getLogger(__name__)



__PAIRS_FILENAME = "pairs.toml"
__SETTINGS_FILENAME = "settings.toml"


class EnvironmentError(Exception):
    """Custom exception for environment-related errors."""
    # Message : "Restart the application to create the settings file."



@dataclass
class Pair:
    source: Path
    destination: Path 

@dataclass
class Settings:
    sender_email: str = ""       # Il faut vérifier que le champ a été rempli à chaque lecture
    sender_email_key: str = field(default="", repr=False)   # Il faut vérifier que le champ a été rempli à chaque lecture
    receivers_emails: list[str] = field(default_factory=list)
    hour: str = "00:00"  # heure par défaut
__DEFAULT_HOUR = "00:00"


# - 1 - Créer les fichiers toml

def ensure_files(config_dir: Path) -> None:
    """Créer le fichier TOML s'il n'existe pas, avec un contenu par défaut.
    """
    pairs_file = config_dir / __PAIRS_FILENAME
    settings_file = config_dir / __SETTINGS_FILENAME

    if not pairs_file.exists():
        logger.debug(f"Creating default pairs file at {pairs_file}")
        write_pairs(config_dir, [])

    if not settings_file.exists():
        logger.debug(f"Creating default settings file at {settings_file}")
        write_settings(config_dir, Settings())

    logger.info(f"Ensured existence of PAIRS_FILE and SETTINGS_FILE")


# - 2 - Lire et écrire dans le fichier des PAIRS de backup

def read_pairs(config_dir: Path) -> list[Pair]:
    """Lit le fichier TOML et renvoie la liste des paires.
    raise ValueError si le fichier est mal formé (mauvais format d'une paire).
    """
    file_path = config_dir / __PAIRS_FILENAME
    try:
        with open(file_path, "rb") as f:
            data = tomllib.load(f)
    except FileNotFoundError:
        logger.error(f"Pairs file not found at {file_path}. Returning empty list.")
        raise EnvironmentError(f"Pairs file not found at {file_path}. You must restart the application to create the pairs file.")
    except tomllib.TOMLDecodeError as e:
        logger.error(f"Error decoding TOML file {file_path}: {e}")
        raise EnvironmentError(f"Error decoding TOML file {file_path}: {e}")

    pairs = []
    for item in data.get("pairs", []):
        try:
            pair = Pair(Path(item["source"]), Path(item["destination"]))
            pairs.append(pair)
        except TypeError as e:
            logger.error(f"Erreur lors de la lecture d'une paire : {e}. Données : {item}")
            raise ValueError(f"Invalid pair data: {item}")
        except KeyError as e:
            logger.error(f"Clé manquante lors de la lecture d'une paire : {e}. Données : {item}")
            raise ValueError(f"Invalid pair data: {item}")
    logger.info(f"Read {len(pairs)} pairs from {file_path}")
    return pairs


def write_pairs(config_dir: Path, pairs: list[Pair]) -> None:
    """Écrit la liste des paires dans le fichier TOML.
    """
    file_path = config_dir / __PAIRS_FILENAME
    data = {"pairs": [
        {"source": str(pair.source), "destination": str(pair.destination)}
        for pair in pairs]}
    try:
        with open(file_path, "wb") as f:
            tomli_w.dump(data, f)
    except Exception as e:
        logger.error(f"Erreur lors de l'écriture des paires dans {file_path} : {e}")
        raise


# - 3 - Lire et écrire dans le fichier des SETTINGS de configuration

def read_settings(config_dir: Path) -> Settings:
    """Lit le fichier TOML et renvoie les paramètres de configuration.
    """
    file_path = config_dir / __SETTINGS_FILENAME
    try:
        with open(file_path, "rb") as f:
            data = tomllib.load(f)
    except FileNotFoundError as e:
        logger.error(f"Settings file not found at {file_path}. Returning default settings.")
        raise EnvironmentError(f"Settings file not found at {file_path}. You must restart the application to create the settings file.")
    except tomllib.TOMLDecodeError as e:
        logger.error(f"Error decoding TOML file {file_path}: {e}")
        raise NotImplementedError(f"Error decoding TOML file {file_path}: {e}")
        # ask Reset the settings to default or Cancel
        return Settings()

    try:
        return Settings(**data.get("settings", {}))
    except TypeError as e:
        logger.error(f"Error creating Settings object: {e}")
        return Settings()


def write_settings(config_dir: Path, settings: Settings) -> None:
    """Écrit les paramètres de configuration dans le fichier TOML.
    """
    file_path = config_dir / __SETTINGS_FILENAME
    data = {
        "settings": asdict(settings)
    }
    try:
        with open(file_path, "wb") as f:
            tomli_w.dump(data, f)
    except Exception as e:
        logger.error(f"Erreur lors de l'écriture des paramètres dans {file_path} : {e}")
        raise


def _read_valid_hour(config_dir: Path) -> tuple[int, int]:
    """Lit le fichier settings.toml et renvoie l'heure de backup.
    Vérifie que l'heure est au format HH:MM.
    """
    settings = read_settings(config_dir)
    hour = settings.hour
    if not isinstance(hour, str) or len(hour) != 5 or hour[2] != ":":
        logger.error(f"Invalid hour format in settings: {hour}. Expected format is HH:MM.")
        raise ValueError(f"Invalid hour format in settings: {hour}. Expected format is HH:MM.")
    h, m = hour.split(":")
    if not (h.isdigit() and m.isdigit() and 0 <= int(h) < 24 and 0 <= int(m) < 60):
        logger.error(f"Invalid hour value in settings: {hour}. Hour must be between 00 and 23, minute between 00 and 59.")
        raise ValueError(f"Invalid hour value in settings: {hour}. Hour must be between 00 and 23, minute between 00 and 59.")
    return int(h), int(m)


def safe_read_hour(config_dir: Path) -> tuple[int, int]:
    """Lit le fichier settings.toml et renvoie les paramètres de configuration.
    Si le fichier est manquant ou mal formé, renvoie les paramètres par défaut.
    """
    def_h, def_m = int(__DEFAULT_HOUR.split(":")[0]), int(__DEFAULT_HOUR.split(":")[1])
    try:
        return _read_valid_hour(config_dir)
    except ValueError as e:
        logger.warning(f"Please check your settings: hour may be invalid. Returning default settings (hour={__DEFAULT_HOUR}).")
        return def_h, def_m
    except (EnvironmentError, NotImplementedError, ValueError) as e:
        logger.error(f"Failed to read settings: {e}. Returning default settings.")
        return def_h, def_m