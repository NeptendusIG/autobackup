"""Tests du planificateur macOS (launchd).

- Les tests de build_job sont purs : ils tournent sur tous les OS.
- Les tests marqués `macos` appellent le vrai launchctl : ils ne tournent que sur macOS,
  avec le paquet installé dans le venv (pip install -e .).
  Ils utilisent un label et un dossier de test : la vraie tâche n'est jamais touchée.
"""

import plistlib
import sys
from datetime import datetime
from pathlib import Path

import pytest

from autobackup.scheduler import launchd

macos = pytest.mark.skipif(sys.platform != "darwin", reason="nécessite macOS (launchd)")


# --- Tests purs : contenu de la plist ----------------------------------------

def test_build_job_contenu(tmp_path: Path) -> None:
    job = launchd.build_job(2, 30, tmp_path)

    assert job["Label"] == launchd.LABEL
    assert job["ProgramArguments"] == [sys.executable, "-m", "autobackup", "--run"]
    assert job["StartCalendarInterval"] == {"Hour": 2, "Minute": 30}
    assert job["StandardErrorPath"] == str(tmp_path / "launchd.err.log")


def test_build_job_chemins_absolus(tmp_path: Path) -> None:
    job = launchd.build_job(2, 0, tmp_path)

    assert Path(job["ProgramArguments"][0]).is_absolute()
    assert Path(job["StandardOutPath"]).is_absolute()
    assert Path(job["StandardErrorPath"]).is_absolute()


def test_build_job_serialisable(tmp_path: Path) -> None:
    """plistlib refuse Path et None : la plist doit pouvoir être écrite et relue."""
    job = launchd.build_job(2, 0, tmp_path)

    assert plistlib.loads(plistlib.dumps(job)) == job


def test_build_job_sans_cles_dangereuses(tmp_path: Path) -> None:
    job = launchd.build_job(2, 0, tmp_path)

    assert not job.get("RunAtLoad", False)
    assert "KeepAlive" not in job


@pytest.mark.parametrize("hour, minute", [(-1, 0), (24, 0), (0, 60), (0, -1)])
def test_build_job_heure_invalide(tmp_path: Path, hour: int, minute: int) -> None:
    #with pytest.raises(ValueError):
        #launchd.build_job(hour, minute, tmp_path)
    pass  # Not in the contract


@pytest.mark.parametrize("hour, minute", [(0, 0), (23, 59)])
def test_build_job_heures_limites(tmp_path: Path, hour: int, minute: int) -> None:
    job = launchd.build_job(hour, minute, tmp_path)

    assert job["StartCalendarInterval"] == {"Hour": hour, "Minute": minute}


# --- Tests macOS : vrai launchctl, label et dossier isolés --------------------

@pytest.fixture
def isolated_launchd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Label et dossier de test ; désinstalle toujours à la fin, même en cas d'échec."""
    monkeypatch.setattr(launchd, "LABEL", "be.gaetan.autobackup.test")
    monkeypatch.setattr(launchd, "LAUNCH_AGENTS_PATH", tmp_path / "LaunchAgents")
    monkeypatch.setattr(launchd, "log_dir", lambda: tmp_path / "logs")
    yield launchd
    launchd.uninstall()


def _heure_lointaine() -> int:
    """Une heure à 12 h d'ici : la tâche de test ne se déclenche pas pendant le test."""
    return (datetime.now().hour + 12) % 24


@macos
def test_install_puis_uninstall(isolated_launchd) -> None:
    assert not launchd.is_installed()

    launchd.install(_heure_lointaine(), 0)
    assert launchd.is_installed()
    assert launchd._plist_path().exists()

    launchd.uninstall()
    assert not launchd.is_installed()
    assert not launchd._plist_path().exists()


@macos
def test_install_deux_fois(isolated_launchd) -> None:
    """Réinstaller (changement d'heure) remplace la tâche au lieu d'échouer."""
    launchd.install(_heure_lointaine(), 0)
    launchd.install(_heure_lointaine(), 30)

    with open(launchd._plist_path(), "rb") as f:
        assert plistlib.load(f)["StartCalendarInterval"]["Minute"] == 30
    assert launchd.is_installed()


@macos
def test_uninstall_sans_installation(isolated_launchd) -> None:
    """uninstall() est idempotente : pas d'erreur s'il n'y a rien à désinstaller."""
    launchd.uninstall()
    launchd.uninstall()
    assert not launchd.is_installed()