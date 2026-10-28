"""
Exceptions pour le package.
"""

# Fonction pour récupérer uniquement les messages d'une chaine :
def describe(exc: BaseException) -> str:
    """Résume une exception et ses causes explicites (`from e`), notes comprises, sans trace."""
    parts = []
    while exc is not None:
        parts.append(f"{type(exc).__name__}: {exc}")
        parts += getattr(exc, "__notes__", [])
        exc = exc.__cause__
    return " ← ".join(parts)

class AutoBackupError(Exception):
    """Classe de base pour les exceptions liées à l'autobackup."""
    pass

class ConfigError(AutoBackupError):
    """Exception levée pour les erreurs de configuration."""
    pass
