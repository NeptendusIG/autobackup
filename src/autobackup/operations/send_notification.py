"""
Opération d'envoyer la notification (NTFY) qui résume les résultats d'un backup.
"""
import logging

from autobackup.backup_results import BackupResult
from autobackup.notify import build_notification, send_notification
from autobackup.pairs import read_settings
from autobackup.paths import config_dir, log_dir


logger = logging.getLogger(__name__)


def manage_send_notification(results: list[BackupResult], critical_message: str | None = None) -> None:
    """Construit puis envoie la notification des résultats du backup.
    Args:
        results: Résultats du backup, un par paire (peut être vide).
        critical_message: Message d'une erreur critique, qui rend la notification prioritaire.
    Raises:
        from read_settings:
            OSError: si une erreur de lecture du fichier settings.toml se produit.
            SettingsError: si le fichier settings.toml est mal formé.
        from send_notification:
            OSError (dont urllib.error.URLError): si l'envoi échoue.
    """

    # - 1 - Lire les paramètres du serveur NTFY
    settings = read_settings(config_dir())
    if not settings.ntfy_topic:
        logger.warning("No ntfy topic configured in settings. Notification not sent.")
        return

    # - 2 - Construire la notification
    notification = build_notification(results, log_dir(), critical_message)
    logger.debug("Notification built: title=%s, priority=%d.", notification.title, notification.priority)

    # - 3 - Envoyer la notification
    send_notification(notification, settings.ntfy_server, settings.ntfy_topic)
    logger.info("Notification envoyée à %s (topic %s).", settings.ntfy_server, settings.ntfy_topic)
