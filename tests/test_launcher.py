import sys
import textwrap

import pytest

import launcher


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher, "_app_dir", lambda: str(tmp_path))
    monkeypatch.setattr(launcher.license_client, "require", lambda **kw: None)
    for m in ("main",):
        sys.modules.pop(m, None)
    yield tmp_path
    sys.modules.pop("main", None)
    sys.path[:] = [p for p in sys.path if str(tmp_path) not in p]


def _main(folder, body):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "main.py").write_text(textwrap.dedent(body), encoding="utf-8")
    (folder / "version.txt").write_text("1.0.0", encoding="utf-8")


def test_runs_src_main(app):
    _main(app / "src", """
        def main():
            open(r"%s", "w").write("ran")
    """ % (app / "out.txt"))
    assert launcher.start([]) == 0
    assert (app / "out.txt").read_text() == "ran"


def test_rolls_back_to_backup_when_new_code_crashes(app):
    _main(app / "src", "def main():\n    raise RuntimeError('bozuk surum')\n")
    _main(app / "src_backup", "def main():\n    open(r'%s', 'w').write('eski')\n" % (app / "out.txt"))
    assert launcher.start([]) == 0
    assert (app / "out.txt").read_text() == "eski"
    assert not (app / "src_backup").exists()


def test_selftest_uses_given_src_and_skips_license(app, monkeypatch):
    calls = []
    monkeypatch.setattr(launcher.license_client, "require", lambda **kw: calls.append(1))
    other = app / "candidate"
    _main(other, "def selftest():\n    return 0\n")
    assert launcher.start(["--selftest", str(other)]) == 0
    assert calls == []


def test_sets_launcher_version_env(app, monkeypatch):
    monkeypatch.delenv("CHECKLIST_LAUNCHER", raising=False)
    _main(app / "src", "def main():\n    pass\n")
    launcher.start([])
    import os
    assert os.environ["CHECKLIST_LAUNCHER"] == str(launcher.LAUNCHER_VERSION)
