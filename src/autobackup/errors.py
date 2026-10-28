"""
Exceptions pour le package.
"""

# Fonction pour récupérer uniquement les messages d'une chaine :
def describe(exc: BaseException|None) -> str:
    """Résume une exception et ses causes explicites (`from e`), notes comprises, sans trace."""
    parts = []
    while exc is not None:
        parts.append(f"{type(exc).__name__}: {exc}")
        parts += getattr(exc, "__notes__", [])
        exc = getattr(exc, "__cause__", None)
    return " ← ".join(parts)

class AutoBackupError(Exception):
    """Classe de base pour les exceptions liées à l'autobackup."""
    pass


# === Exceptions sur les fichiers de données ===
class ConfigError(AutoBackupError):
    """Exception levée pour les erreurs de configuration."""
    pass

class PairsError(ConfigError):
    """Exception levée pour les erreurs liées aux paires de répertoires."""
    pass

class SettingsError(ConfigError):
    """Exception levée pour les erreurs liées aux paramètres de configuration."""
    pass


# === Exceptions sur le planificateur ===
class SchedulerError(AutoBackupError):
    """Échec de l'installation ou de la désinstallation de la tâche planifiée."""
