"""
"""
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class BackupResult:
    """Représente le résultat d'une opération de backup pour une paire source-destination."""
    source: str
    success: bool
    destination: str = ""
    name: str = ""  # Nom de la source (parents/dirname)
    number_files: int = -1
    #horodatage: str = ""
    #name: str = ""
    #message: str = ""  # Message d'erreur ou d'information
    snapshot: str = ""
    error: str = ""
