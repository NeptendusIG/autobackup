"""Tests de la partie ntfy de autobackup.notify.

Aucun accès à Internet : l'envoi est testé contre un petit serveur HTTP
local, lancé dans un thread sur 127.0.0.1 avec un port choisi par l'OS.
"""

import string
import threading
import urllib.request
from email.header import decode_header, make_header
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from autobackup.backup_results import BackupResult
from autobackup.notify import (
    MAX_MESSAGE_BYTES,
    Notification,
    _rfc2047,
    _truncate,
    build_notification,
    new_topic,
    send_notification,
)

LOG_DIR = Path("/inexistant/logs")  # build_notification ne doit pas toucher au disque


def ok(source: str = "/src/a") -> BackupResult:
    return BackupResult(source, True, "/dst/a", snapshot="2026-10-24_02-00-00")


def ko(source: str = "/src/b", error: str = "Permission refusée") -> BackupResult:
    return BackupResult(source, False, "/dst/b", error=error)


def decode_rfc2047(value: str) -> str:
    return str(make_header(decode_header(value)))


# --- build_notification : fonction pure ---------------------------------------


def test_succes():
    n = build_notification([ok(), ok("/src/c")], LOG_DIR)
    assert n.priority == 3
    assert n.tags == ["white_check_mark"]
    assert "Succès" in n.title and "2 paire(s)" in n.title
    assert "2026-10-24_02-00-00" in n.message


def test_echec_partiel():
    n = build_notification([ok(), ko()], LOG_DIR)
    assert n.priority == 4
    assert n.tags == ["x"]
    assert "ÉCHEC" in n.title and "1/2" in n.title
    assert "Permission refusée" in n.message
    assert "/src/b" in n.message


def test_aucune_paire_est_un_echec():
    # Ne rien sauvegarder n'est pas un succès : c'est le cas le plus traître.
    n = build_notification([], LOG_DIR)
    assert n.priority == 4
    assert n.tags == ["x"]
    assert "aucune paire" in n.title


def test_le_message_commence_par_le_titre():
    n = build_notification([ok()], LOG_DIR)
    assert n.message.splitlines()[0] == n.title


def test_message_long_tronque():
    erreur = "é" * 10_000  # 2 octets par caractère
    n = build_notification([ko(error=erreur)], LOG_DIR)
    assert len(n.message.encode("utf-8")) <= MAX_MESSAGE_BYTES
    assert n.message.endswith("(tronqué, voir le log)")


# --- _truncate ------------------------------------------------------------------


def test_truncate_texte_court_inchange():
    assert _truncate("court") == "court"


def test_truncate_exactement_a_la_limite_inchange():
    texte = "a" * 100
    assert _truncate(texte, limit=100) == texte


@pytest.mark.parametrize("char", ["a", "é", "€", "😀"])  # 1, 2, 3 et 4 octets
def test_truncate_respecte_la_limite_et_les_caracteres(char):
    resultat = _truncate(char * 1000, limit=200)
    data = resultat.encode("utf-8")  # échouerait si un caractère était coupé
    assert len(data) <= 200
    assert resultat.endswith("(tronqué, voir le log)")
    assert set(resultat.split("\n")[0]) == {char}


# --- _rfc2047 -----------------------------------------------------------------


def test_rfc2047_ascii_inchange():
    assert _rfc2047("Backup OK") == "Backup OK"


@pytest.mark.parametrize("valeur", ["Succès", "❌ ÉCHEC : 1/2", "✅ ok 😀"])
def test_rfc2047_aller_retour(valeur):
    encode = _rfc2047(valeur)
    assert encode.isascii()  # un en-tête HTTP doit être ASCII
    assert decode_rfc2047(encode) == valeur


# --- new_topic ----------------------------------------------------------------


def test_new_topic_format():
    topic = new_topic()
    assert topic.startswith("autobackup-")
    alea = topic.removeprefix("autobackup-")
    assert len(alea) == 10
    assert set(alea) <= set(string.ascii_lowercase + string.digits)


def test_new_topic_longueur_parametrable():
    assert len(new_topic(16).removeprefix("autobackup-")) == 16


def test_new_topic_aleatoire():
    assert len({new_topic() for _ in range(100)}) == 100


# --- send_notification : serveur HTTP local -------------------------------------


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        longueur = int(self.headers.get("Content-Length", 0))
        self.server.requests.append(
            {
                "path": self.path,
                "headers": dict(self.headers),
                "body": self.rfile.read(longueur),
            }
        )
        self.send_response(self.server.status)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, *args):  # silence dans la sortie de pytest
        pass


@pytest.fixture(autouse=True)
def sans_proxy(monkeypatch):
    """Empêche urllib de passer par un proxy système pour joindre 127.0.0.1."""
    for var in ("http_proxy", "HTTP_PROXY", "https_proxy", "HTTPS_PROXY",
                "all_proxy", "ALL_PROXY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("no_proxy", "127.0.0.1,localhost")
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")
    # urlopen met son « opener » en cache au premier appel, proxys compris.
    monkeypatch.setattr(urllib.request, "_opener", None)


@pytest.fixture
def serveur():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    srv.requests = []
    srv.status = 200
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    srv.url = f"http://127.0.0.1:{srv.server_address[1]}"
    yield srv
    srv.shutdown()
    srv.server_close()


NOTIF = Notification(title="❌ ÉCHEC : 1/2", message="détail\nligne 2",
                     priority=4, tags=["x"])


def test_envoi_requete(serveur):
    send_notification(NOTIF, serveur.url, "autobackup-abc123")
    (req,) = serveur.requests
    assert req["path"] == "/autobackup-abc123"
    assert req["body"].decode("utf-8") == "détail\nligne 2"
    assert decode_rfc2047(req["headers"]["Title"]) == "❌ ÉCHEC : 1/2"
    assert req["headers"]["Priority"] == "4"
    assert req["headers"]["Tags"] == "x"
    assert "Authorization" not in req["headers"]


def test_envoi_avec_token(serveur):
    send_notification(NOTIF, serveur.url, "t", token="tk_secret")
    assert serveur.requests[0]["headers"]["Authorization"] == "Bearer tk_secret"


def test_slash_final_du_serveur(serveur):
    send_notification(NOTIF, serveur.url + "/", "t")
    assert serveur.requests[0]["path"] == "/t"


def test_plusieurs_tags(serveur):
    notif = Notification("ok", "m", 3, ["white_check_mark", "floppy_disk"])
    send_notification(notif, serveur.url, "t")
    assert serveur.requests[0]["headers"]["Tags"] == "white_check_mark,floppy_disk"


@pytest.mark.parametrize("status", [401, 403, 429, 500])
def test_erreur_http_leve_oserror(serveur, status):
    # Token refusé, sujet protégé, limite de débit, panne du serveur.
    serveur.status = status
    with pytest.raises(OSError):
        send_notification(NOTIF, serveur.url, "t")


def test_serveur_injoignable_leve_oserror():
    # On réserve un port puis on le libère : personne n'y écoute.
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    port = srv.server_address[1]
    srv.server_close()
    with pytest.raises(OSError):
        send_notification(NOTIF, f"http://127.0.0.1:{port}", "t")


def test_chaine_complete(serveur):
    """build_notification → send_notification : ce que reçoit vraiment le téléphone."""
    notif = build_notification([ok(), ko()], LOG_DIR)
    send_notification(notif, serveur.url, "t")
    req = serveur.requests[0]
    assert decode_rfc2047(req["headers"]["Title"]) == notif.title
    assert req["body"].decode("utf-8") == notif.message
