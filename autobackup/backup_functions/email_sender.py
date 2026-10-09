"""
Envoi des mails de notification (SMTP Gmail).

Identifiants lus dans main_settings.json (à la racine du package autobackup).
"""
import logging
import smtplib
from email.message import EmailMessage
from pathlib import Path

from utility import File

log = logging.getLogger(__name__)

SETTINGS_FILE = str(Path(__file__).resolve().parents[1] / "main_settings.json")
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


class OutNetwork:

    @classmethod
    def send_notif_mail(cls, receiver, message, subject="NOTIFICATION"):
        """Envoie un mail de notification.
        @pre: receiver (adresse), message (texte), subject
        @post: True si le mail est parti, False sinon (erreur loggée)
        """
        # SENDER CONFIG
        try:
            sender: str = str(File.JsonFile.get_value(SETTINGS_FILE, "sender_mail", default=""))
            psw: str= str(File.JsonFile.get_value(SETTINGS_FILE, "sender_mail_key", default=""))
        except Exception as e:
            log.warning(f"Couldn't (get) SETTINGS mail sender : {e}")
            return False
        # CONTENT (EmailMessage encode en UTF-8 : accents acceptés)
        mail = EmailMessage()
        mail["Subject"] = subject
        mail["From"] = sender
        mail["To"] = receiver
        mail.set_content(message)
        # SENDING
        try:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(sender, psw)
                server.send_message(mail)
        except (smtplib.SMTPException, OSError) as e:
            log.error(f"Mail not sent (subject: {subject}) : {e}")
            return False
        log.info(f"Mail sent (subject: {subject})")
        return True
