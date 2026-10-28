"""Tests du planificateur Windows (schtasks).

- Tests purs (build_task_xml, _next_start) : tournent sur tous les OS.
- Tests avec subprocess simulé : vérifient les commandes envoyées à schtasks, sur tous les OS.
- Tests marqués `windows` : appellent le vrai schtasks ; seulement sous Windows, avec le paquet
  installé dans le venv (pip install -e .). Ils utilisent un nom de tâche de test.
"""

import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import pytest

from autobackup.scheduler import windows
from autobackup.errors import SchedulerError

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="nécessite Windows (schtasks)")

NS = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}
NOW = datetime(2026, 10, 19, 9, 44)


def _parse(xml: str) -> ET.Element:
    return ET.fromstring(xml)


def _text(root: ET.Element, path: str) -> str:
    element = root.find(path, NS)
    assert element is not None, f"élément absent : {path}"
    assert element.text is not None, f"élément vide : {path}"
    return element.text


# --- Tests purs : prochaine occurrence ---------------------------------------

def test_next_start_heure_passee_donne_demain() -> None:
    assert windows._next_start(2, 0, NOW) == datetime(2026, 10, 20, 2, 0)


def test_next_start_heure_a_venir_donne_aujourdhui() -> None:
    assert windows._next_start(23, 30, NOW) == datetime(2026, 10, 19, 23, 30)


def test_next_start_minute_exacte_donne_demain() -> None:
    """À l'instant même, l'occurrence du jour est considérée comme passée."""
    assert windows._next_start(9, 44, NOW) == datetime(2026, 10, 20, 9, 44)


# --- Tests purs : contenu du XML ---------------------------------------------

def test_xml_declenchement_quotidien() -> None:
    root = _parse(windows.build_task_xml(2, 0, with_password=True, now=NOW))

    assert _text(root, "t:Triggers/t:CalendarTrigger/t:StartBoundary") == "2026-10-20T02:00:00"
    assert _text(root, "t:Triggers/t:CalendarTrigger/t:ScheduleByDay/t:DaysInterval") == "1"


def test_xml_commande() -> None:
    root = _parse(windows.build_task_xml(2, 0, with_password=True, now=NOW))

    assert _text(root, "t:Actions/t:Exec/t:Command") == sys.executable
    assert Path(_text(root, "t:Actions/t:Exec/t:Command")).is_absolute()
    assert _text(root, "t:Actions/t:Exec/t:Arguments") == "-m autobackup --run"


def test_xml_reglages_importants() -> None:
    root = _parse(windows.build_task_xml(2, 0, with_password=True, now=NOW))

    assert _text(root, "t:Settings/t:StartWhenAvailable") == "true"
    assert _text(root, "t:Settings/t:MultipleInstancesPolicy") == "IgnoreNew"
    assert _text(root, "t:Settings/t:DisallowStartIfOnBatteries") == "false"
    assert _text(root, "t:Settings/t:ExecutionTimeLimit") == "PT12H"


@pytest.mark.parametrize("with_password, logon", [(True, "Password"), (False, "InteractiveToken")])
def test_xml_type_de_session(with_password: bool, logon: str) -> None:
    root = _parse(windows.build_task_xml(2, 0, with_password=with_password, now=NOW))

    assert _text(root, "t:Principals/t:Principal/t:LogonType") == logon


def test_xml_echappe_les_caracteres_speciaux(monkeypatch: pytest.MonkeyPatch) -> None:
    exe = r"C:\Users\A&B <test>\venv\Scripts\python.exe"
    monkeypatch.setattr(windows.sys, "executable", exe)

    xml = windows.build_task_xml(2, 0, with_password=True, now=NOW)

    assert "A&amp;B &lt;test&gt;" in xml
    assert _text(_parse(xml), "t:Actions/t:Exec/t:Command") == exe


@pytest.mark.parametrize("hour, minute", [(-1, 0), (24, 0), (0, 60), (0, -1)])
def test_xml_heure_invalide(hour: int, minute: int) -> None:
    with pytest.raises(ValueError):
        windows.build_task_xml(hour, minute, with_password=True, now=NOW)


# --- Tests avec subprocess simulé : commandes envoyées à schtasks -------------

class FakeRun:
    """Remplace subprocess.run : enregistre les appels, simule un code de retour."""

    def __init__(self, returncode: int = 0, stderr: str = "") -> None:
        self.calls: list[list[str]] = []
        self.xml_bytes: bytes | None = None
        self.returncode = returncode
        self.stderr = stderr

    def __call__(self, args, check=False, **kwargs):
        self.calls.append(list(args))
        if "/XML" in args:  # le fichier est supprimé après l'appel : on le lit maintenant
            self.xml_bytes = Path(args[args.index("/XML") + 1]).read_bytes()
        code = 0 if args[0] == sys.executable else self.returncode
        if check and code != 0:
            raise subprocess.CalledProcessError(code, args, output="", stderr=self.stderr)
        return subprocess.CompletedProcess(args, code, stdout="", stderr=self.stderr)

    def schtasks_calls(self) -> list[list[str]]:
        return [c for c in self.calls if c[0] == "schtasks"]


@pytest.fixture
def fake_run(monkeypatch: pytest.MonkeyPatch) -> FakeRun:
    fake = FakeRun()
    monkeypatch.setattr(windows.subprocess, "run", fake)
    return fake


def test_install_avec_mot_de_passe(fake_run: FakeRun) -> None:
    windows.install(2, 0, password="secret")

    (create,) = fake_run.schtasks_calls()
    assert create[:2] == ["schtasks", "/Create"]
    assert create[create.index("/TN") + 1] == windows.TASK_NAME
    assert "/F" in create
    assert create[create.index("/RU") + 1] == windows._account()
    assert create[create.index("/RP") + 1] == "secret"


def test_install_sans_mot_de_passe(fake_run: FakeRun) -> None:
    windows.install(2, 0)

    (create,) = fake_run.schtasks_calls()
    assert "/RU" not in create and "/RP" not in create
    assert fake_run.xml_bytes is not None
    root = _parse(fake_run.xml_bytes.decode("utf-16").split("\n", 1)[1])
    assert _text(root, "t:Principals/t:Principal/t:LogonType") == "InteractiveToken"


def test_install_ecrit_le_xml_en_utf16(fake_run: FakeRun) -> None:
    windows.install(2, 0, password="secret")

    assert fake_run.xml_bytes is not None
    assert fake_run.xml_bytes.startswith(b"\xff\xfe")  # BOM UTF-16
    text = fake_run.xml_bytes.decode("utf-16")
    assert text.startswith('<?xml version="1.0" encoding="UTF-16"?>')
    _parse(text.split("\n", 1)[1])  # le corps est un XML valide


def test_install_verifie_l_import_avant_schtasks(fake_run: FakeRun) -> None:
    windows.install(2, 0)

    assert fake_run.calls[0][:2] == [sys.executable, "-c"]


def test_install_echec_schtasks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(windows.subprocess, "run", FakeRun(returncode=1, stderr="Accès refusé."))

    with pytest.raises(SchedulerError, match="Accès refusé"):
        windows.install(2, 0)


def test_uninstall_sans_tache_n_appelle_pas_delete(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeRun(returncode=1)  # /Query échoue : la tâche n'existe pas
    monkeypatch.setattr(windows.subprocess, "run", fake)

    windows.uninstall()

    assert all("/Delete" not in c for c in fake.calls)


# --- Tests Windows : vrai schtasks, nom de tâche isolé ------------------------

@pytest.fixture
def isolated_task(monkeypatch: pytest.MonkeyPatch):
    """Nom de tâche de test ; supprime toujours la tâche à la fin, même en cas d'échec."""
    monkeypatch.setattr(windows, "TASK_NAME", "AutobackupTest")
    yield windows
    windows.uninstall()


def _heure_lointaine() -> int:
    return (datetime.now().hour + 12) % 24


@windows_only
def test_install_puis_uninstall(isolated_task) -> None:
    assert not windows.is_installed()

    windows.install(_heure_lointaine(), 0)  # sans mot de passe : pas de secret dans les tests
    assert windows.is_installed()

    windows.uninstall()
    assert not windows.is_installed()


@windows_only
def test_install_deux_fois(isolated_task) -> None:
    """/F : réinstaller remplace la tâche au lieu d'échouer."""
    windows.install(_heure_lointaine(), 0)
    windows.install(_heure_lointaine(), 30)

    assert windows.is_installed()


@windows_only
def test_uninstall_sans_installation(isolated_task) -> None:
    windows.uninstall()
    windows.uninstall()

    assert not windows.is_installed()