"""Transforme les résultats d'un backup en mail et l'envoie."""

import smtplib
import ssl
from pathlib import Path
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

import string
import base64
import secrets
import urllib.request
from dataclasses import dataclass

from autobackup.backup_results import BackupResult

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465


def build_report_email(results: list[BackupResult],
                 sender: str, receivers: list[str]) -> EmailMessage:
    """Fonction pure : construit le message complet. Testable sans réseau."""
    failures = [r for r in results if not r.success]
    if not results:
        status = "❌ ÉCHEC : aucune paire configurée, rien n'a été sauvegardé"
    elif failures:
        status = f"❌ ÉCHEC : {len(failures)}/{len(results)} paire(s) en erreur"
    else:
        status = f"✅ Succès : {len(results)} paire(s) sauvegardée(s)"

    lines = [status, ""]
    for r in results:
        lines.append(f"{'OK    ' if r.success else 'ÉCHEC '} {r.source} → {r.destination}")
        if r.snapshot:
            lines.append(f"       instantané : {r.snapshot}")
        if r.error:
            lines.append(f"       erreur : {r.error}")

    msg = EmailMessage()
    msg["Subject"] = f"[autobackup] {status}"
    msg["From"] = sender
    msg["To"] = receivers
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()
    msg.set_content("\n".join(lines))
    return msg


def send_email(msg: EmailMessage, sender: str, app_password: str) -> None:
    """Envoie le message ; lève OSError (dont smtplib.SMTPException) en cas d'échec."""
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context, timeout=30) as smtp:
        smtp.login(sender, app_password)
        smtp.send_message(msg)


# === Notification via NTFY ===
MAX_MESSAGE_BYTES = 4096 
_ALPHABET = string.ascii_lowercase + string.digits  # facile à taper sur un téléphone


@dataclass
class Notification:
    title: str
    message: str
    priority: int
    tags: list[str]

def build_notification(results: list[BackupResult], log_dir: Path, critical_message: str | None = None) -> Notification:
    """Construit la notification à envoyer via NTFY."""
    failures = [r for r in results if not r.success]
    tags = []
    if critical_message:
        status = f"ÉCHEC CRITIQUE : {critical_message}"
        priority = 5
        tags.append("x")
    elif not results:
        status = "ÉCHEC : aucune paire configurée, rien n'a été sauvegardé"
        priority = 4
        tags.append("x")
    elif failures:
        status = f"ÉCHEC : {len(failures)}/{len(results)} paire(s) en erreur"
        priority = 4
        tags.append("x")
    else:
        status = f"Succès : {len(results)} paire(s) sauvegardée(s)"
        priority = 3
        tags.append("white_check_mark")


    lines = [status, ""]
    if critical_message:
        lines.append(f"Message critique : {critical_message}")
        lines.append("")
    for r in results:
        lines.append(f"{r.name or r.source} : {'OK' if r.success else 'ÉCHEC'}")
        if r.snapshot:
            lines.append(f"       Dossier produit : {r.snapshot}")
        if r.error:
            lines.append(f"       erreur : {r.error}")
    if log_dir:
        lines.append("")
        lines.append(f"Voir le log complet : {log_dir}")

    message = _truncate("\n".join(lines))
    return Notification(title=status, message=message, priority=priority, tags=tags)


def _truncate(text: str, limit: int = MAX_MESSAGE_BYTES) -> str:
    """Coupe le texte à `limit` octets UTF-8 sans couper un caractère en deux."""
    data = text.encode("utf-8")
    if len(data) <= limit:
        return text
    suffix = "\n… (tronqué, voir le log)"
    cut = data[: limit - len(suffix.encode("utf-8"))]
    return cut.decode("utf-8", errors="ignore") + suffix


def _rfc2047(value: str) -> str:
    """Encode un en-tête HTTP non ASCII (accents, emoji), comme le permet ntfy."""
    if value.isascii():
        return value
    return "=?UTF-8?B?" + base64.b64encode(value.encode("utf-8")).decode("ascii") + "?="


def send_notification(notification: Notification, server: str, topic: str, token: str | None = None) -> None:
    """Publie la notification ; lève OSError (dont urllib.error.URLError) en cas d'échec.
    Raises:
        OSError (dont urllib.error.URLError) si l'envoi échoue.
    """
    headers = {
        "Title": _rfc2047(notification.title),
        "Priority": str(notification.priority),
        "Tags": ",".join(notification.tags),
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"{server.rstrip('/')}/{topic}",
                                     data=notification.message.encode("utf-8"),
                                     headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=30):
        pass


def new_topic(length: int = 10) -> str:
    """Nom de sujet aléatoire, environ 72 bits d'aléa : hors d'atteinte d'une recherche exhaustive."""
    return "autobackup-" + "".join(secrets.choice(_ALPHABET) for _ in range(length))