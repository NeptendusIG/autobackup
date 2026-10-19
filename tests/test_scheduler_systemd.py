"""Tests du planificateur Linux (timer systemd utilisateur).

- Tests purs (build_service, build_timer, _quote) : tournent sur tous les OS.
- Tests avec subprocess simulé : vérifient les fichiers écrits et les commandes systemctl.
- Tests marqués `systemd` : appellent le vrai systemctl --user ; seulement sous Linux avec une
  session systemd utilisateur, et le paquet installé dans le venv (pip install -e .).
  Ils utilisent un nom d'unité de test.
"""

import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from autobackup.scheduler import systemd
from autobackup.scheduler.errors import SchedulerError


def _user_systemd_available() -> bool:
    if not sys.platform.startswith("linux") or shutil.which("systemctl") is None:
        return False
    result = subprocess.run(["systemctl", "--user", "show-environment"], capture_output=True)
    return result.returncode == 0


systemd_only = pytest.mark.skipif(not _user_systemd_available(),
                                  reason="nécessite une session systemd utilisateur")


def _exec_start(service: str) -> str:
    (line,) = [l for l in service.splitlines() if l.startswith("ExecStart=")]
    return line.removeprefix("ExecStart=")


# --- Tests purs : échappement d'ExecStart ------------------------------------

def test_quote_simple() -> None:
    assert systemd._quote("--run") == '"--run"'


def test_quote_espaces() -> None:
    assert systemd._quote("/opt/mon venv/python") == '"/opt/mon venv/python"'


def test_quote_caracteres_speciaux_argument() -> None:
    assert systemd._quote('a "b" \\ 50% $X') == '"a \\"b\\" \\\\ 50%% $$X"'


def test_quote_dollar_executable_non_double() -> None:
    """systemd ne développe pas $ dans le chemin de l'exécutable : il doit rester simple."""
    assert systemd._quote("/opt/$dir/python", executable=True) == '"/opt/$dir/python"'


# --- Tests purs : contenu des unités ------------------------------------------

def test_service(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(systemd.sys, "executable", "/home/g/venv/bin/python")

    service = systemd.build_service()

    assert "Type=oneshot" in service
    assert _exec_start(service) == '"/home/g/venv/bin/python" "-m" "autobackup" "--run"'


def test_service_executable_absolu() -> None:
    exe = _exec_start(systemd.build_service()).split('"')[1]

    assert Path(exe).is_absolute()


def test_timer() -> None:
    timer = systemd.build_timer(2, 5)

    assert "OnCalendar=*-*-* 02:05:00" in timer
    assert "Persistent=true" in timer
    assert "WantedBy=timers.target" in timer


@pytest.mark.parametrize("hour, minute", [(-1, 0), (24, 0), (0, 60), (0, -1)])
def test_timer_heure_invalide(hour: int, minute: int) -> None:
    with pytest.raises(ValueError):
        systemd.build_timer(hour, minute)


def test_unit_dir_respecte_xdg(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    assert systemd._unit_dir() == tmp_path / "systemd" / "user"


@pytest.mark.skipif(shutil.which("systemd-analyze") is None, reason="systemd-analyze absent")
def test_unites_valides_selon_systemd(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """systemd-analyze verify relit les unités comme systemd (syntaxe et exécutable)."""
    exe_dir = tmp_path / "venv avec espace"
    exe_dir.mkdir()
    (exe_dir / "python").symlink_to(sys.executable)
    monkeypatch.setattr(systemd.sys, "executable", str(exe_dir / "python"))
    (tmp_path / "autobackup.service").write_text(systemd.build_service())
    (tmp_path / "autobackup.timer").write_text(systemd.build_timer(2, 0))

    result = subprocess.run(["systemd-analyze", "verify", "--man=no",
                             "autobackup.service", "autobackup.timer"],
                            cwd=tmp_path, capture_output=True, text=True)

    assert result.returncode == 0, result.stderr


# --- Tests avec subprocess simulé ---------------------------------------------

class FakeRun:
    def __init__(self, returncode: int = 0, stderr: str = "") -> None:
        self.calls: list[list[str]] = []
        self.returncode = returncode
        self.stderr = stderr

    def __call__(self, args, check=False, **kwargs):
        self.calls.append(list(args))
        code = 0 if args[0] == sys.executable else self.returncode
        if check and code != 0:
            raise subprocess.CalledProcessError(code, args, output="", stderr=self.stderr)
        return subprocess.CompletedProcess(args, code, stdout="", stderr=self.stderr)

    def systemctl_calls(self) -> list[list[str]]:
        return [c[2:] for c in self.calls if c[:2] == ["systemctl", "--user"]]


@pytest.fixture
def fake_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> FakeRun:
    fake = FakeRun()
    monkeypatch.setattr(systemd.subprocess, "run", fake)
    monkeypatch.setattr(systemd, "_systemctl_available", lambda: True)
    monkeypatch.setattr(systemd, "_unit_dir", lambda: tmp_path / "units")
    return fake


def test_install_ecrit_les_unites(fake_env: FakeRun, tmp_path: Path) -> None:
    systemd.install(2, 0)

    units = tmp_path / "units"
    assert (units / "autobackup.service").read_text() == systemd.build_service()
    assert (units / "autobackup.timer").read_text() == systemd.build_timer(2, 0)


def test_install_commandes_systemctl(fake_env: FakeRun) -> None:
    systemd.install(2, 0)

    assert fake_env.systemctl_calls()[:3] == [
        ["daemon-reload"],
        ["enable", "--now", "autobackup.timer"],
        ["restart", "autobackup.timer"],
    ]


def test_install_ignore_le_mot_de_passe(fake_env: FakeRun) -> None:
    systemd.install(2, 0, password="inutile")

    assert all("inutile" not in " ".join(c) for c in fake_env.calls)


def test_install_sans_systemd(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(systemd, "_systemctl_available", lambda: False)

    with pytest.raises(SchedulerError, match="systemd n'est pas disponible"):
        systemd.install(2, 0)


def test_install_echec_systemctl(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(systemd.subprocess, "run", FakeRun(returncode=1, stderr="Failed to connect to bus"))
    monkeypatch.setattr(systemd, "_systemctl_available", lambda: True)
    monkeypatch.setattr(systemd, "_unit_dir", lambda: tmp_path)

    with pytest.raises(SchedulerError, match="Failed to connect to bus"):
        systemd.install(2, 0)


def test_uninstall_supprime_les_fichiers(fake_env: FakeRun, tmp_path: Path) -> None:
    systemd.install(2, 0)
    systemd.uninstall()

    assert not (tmp_path / "units" / "autobackup.service").exists()
    assert not (tmp_path / "units" / "autobackup.timer").exists()
    assert ["disable", "--now", "autobackup.timer"] in fake_env.systemctl_calls()


def test_is_installed_sans_systemd(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(systemd, "_systemctl_available", lambda: False)

    assert systemd.is_installed() is False


# --- Tests systemd : vrai systemctl --user, nom d'unité isolé ------------------

@pytest.fixture
def isolated_units(monkeypatch: pytest.MonkeyPatch):
    """Nom d'unité de test ; désinstalle toujours à la fin, même en cas d'échec."""
    monkeypatch.setattr(systemd, "UNIT_NAME", "autobackup-test")
    yield systemd
    systemd.uninstall()


def _heure_lointaine() -> int:
    return (datetime.now().hour + 12) % 24


@systemd_only
def test_install_puis_uninstall(isolated_units) -> None:
    assert not systemd.is_installed()

    systemd.install(_heure_lointaine(), 0)
    assert systemd.is_installed()
    assert systemd._timer_path().exists()

    systemd.uninstall()
    assert not systemd.is_installed()
    assert not systemd._timer_path().exists()


@systemd_only
def test_install_deux_fois(isolated_units) -> None:
    systemd.install(_heure_lointaine(), 0)
    systemd.install(_heure_lointaine(), 30)

    assert f":30:00" in systemd._timer_path().read_text()
    assert systemd.is_installed()


@systemd_only
def test_uninstall_sans_installation(isolated_units) -> None:
    systemd.uninstall()
    systemd.uninstall()

    assert not systemd.is_installed()
