"""Tests de autobackup.backup_functions.email_sender (SMTP et settings mockés)."""
import smtplib
from unittest.mock import MagicMock, patch

import pytest

from autobackup.backup_functions import email_sender
from autobackup.backup_functions.email_sender import OutNetwork

SETTINGS = {"sender_mail": "bot@example.com", "sender_mail_key": "secret"}


def fake_get_value(_file, key, default=None):
    return SETTINGS.get(key, default)


@pytest.fixture
def smtp():
    """Remplace smtplib.SMTP ; renvoie le serveur (mock) utilisé dans le with."""
    with patch.object(email_sender.smtplib, "SMTP") as smtp_cls:
        server = smtp_cls.return_value.__enter__.return_value
        server.smtp_cls = smtp_cls
        yield server


@pytest.fixture(autouse=True)
def settings():
    with patch.object(email_sender.File.JsonFile, "get_value", side_effect=fake_get_value) as m:
        yield m


def test_send_success(smtp):
    assert OutNetwork.send_notif_mail("dest@example.com", "Bonjour é", "Sujet") is True

    smtp.smtp_cls.assert_called_once_with(email_sender.SMTP_HOST, email_sender.SMTP_PORT)
    smtp.starttls.assert_called_once()
    smtp.login.assert_called_once_with("bot@example.com", "secret")
    smtp.send_message.assert_called_once()


def test_message_content(smtp):
    OutNetwork.send_notif_mail("dest@example.com", "Corps du message", "Mon sujet")

    mail = smtp.send_message.call_args.args[0]
    assert mail["Subject"] == "Mon sujet"
    assert mail["From"] == "bot@example.com"
    assert mail["To"] == "dest@example.com"
    assert "Corps du message" in mail.get_content()


def test_default_subject(smtp):
    OutNetwork.send_notif_mail("dest@example.com", "msg")

    assert smtp.send_message.call_args.args[0]["Subject"] == "NOTIFICATION"


def test_settings_read_from_settings_file(smtp, settings):
    OutNetwork.send_notif_mail("dest@example.com", "msg")

    keys = [c.args[1] for c in settings.call_args_list]
    assert keys == ["sender_mail", "sender_mail_key"]
    assert all(c.args[0] == email_sender.SETTINGS_FILE for c in settings.call_args_list)


def test_settings_error_returns_false(smtp, settings):
    settings.side_effect = KeyError("boom")

    assert OutNetwork.send_notif_mail("dest@example.com", "msg") is False
    smtp.smtp_cls.assert_not_called()


@pytest.mark.parametrize("step", ["starttls", "login", "send_message"])
def test_smtp_exception_returns_false(smtp, step):
    getattr(smtp, step).side_effect = smtplib.SMTPException("fail")

    assert OutNetwork.send_notif_mail("dest@example.com", "msg") is False


def test_connection_error_returns_false(smtp):
    smtp.smtp_cls.side_effect = OSError("network down")

    assert OutNetwork.send_notif_mail("dest@example.com", "msg") is False
