"""Transforme les résultats d'un backup en mail et l'envoie."""

import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path

from autobackup.backup_results import BackupResult

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465


def build_report(results: list[BackupResult],
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


def send(msg: EmailMessage, sender: str, app_password: str) -> None:
    """Envoie le message ; lève OSError (dont smtplib.SMTPException) en cas d'échec."""
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context, timeout=30) as smtp:
        smtp.login(sender, app_password)
        smtp.send_message(msg)