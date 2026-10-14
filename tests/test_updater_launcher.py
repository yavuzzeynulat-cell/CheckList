import updater

SETUP = dict(setup_url="https://x/CheckList-Setup.exe", setup_sha256="a" * 64)


def _info(**kw):
    base = dict(version="9.9.9", notes="", asset_url="https://x/src.zip", sha256="b" * 64)
    base.update(kw)
    return updater.UpdateInfo(**base)


def test_old_launcher_forces_setup(monkeypatch):
    monkeypatch.setattr(updater, "gate_present", lambda: True)
    monkeypatch.setattr(updater, "MIN_LAUNCHER", 2)
    monkeypatch.setenv("CHECKLIST_LAUNCHER", "1")
    assert updater.decide_update_kind(_info(**SETUP)) == "required"


def test_current_launcher_takes_code_path(monkeypatch):
    monkeypatch.setattr(updater, "gate_present", lambda: True)
    monkeypatch.setattr(updater, "MIN_LAUNCHER", 1)
    monkeypatch.setenv("CHECKLIST_LAUNCHER", "1")
    assert updater.decide_update_kind(_info(**SETUP)) == "code"


def test_missing_env_means_dev_run(monkeypatch):
    monkeypatch.delenv("CHECKLIST_LAUNCHER", raising=False)
    assert updater.launcher_version() == 0


def test_release_notes_declare_min_launcher(monkeypatch):
    # Kod, kurulu (eski) src'nin sabitine degil, yeni release'in beyanina
    # bakmali: eski src kendi MIN_LAUNCHER'ini zaten karsiliyor.
    monkeypatch.setattr(updater, "gate_present", lambda: True)
    monkeypatch.setenv("CHECKLIST_LAUNCHER", "1")
    info = _info(notes="Yeni\n\nMIN_LAUNCHER: 2\nSHA256: " + "b" * 64, **SETUP)
    assert updater.decide_update_kind(info) == "required"


def test_min_launcher_line_hidden_from_user():
    assert "MIN_LAUNCHER" not in updater._visible_notes("Yeni\nMIN_LAUNCHER: 2")


def test_needed_launcher_parsed():
    assert updater.required_launcher("x\nMIN_LAUNCHER: 3\n") == 3
    assert updater.required_launcher("x") == 0


def test_successful_code_update_restarts_without_extra_dialog(monkeypatch):
    # "Update complete" kutusu OK'e kadar eski pencereyi acik tutuyordu.
    from tkinter import messagebox
    shown, restarted = [], []
    monkeypatch.setattr(updater, "decide_update_kind", lambda info: "code")
    monkeypatch.setattr(updater, "download_update", lambda info, dest, progress=None: True)
    monkeypatch.setattr(updater, "apply_update", lambda p: None)
    monkeypatch.setattr(updater, "restart_app", lambda: restarted.append(1))
    monkeypatch.setattr(messagebox, "showinfo", lambda *a, **k: shown.append(a))
    updater.run_update_flow(_info())
    assert restarted == [1] and shown == []


def test_download_update_reports_progress(monkeypatch, tmp_path):
    calls = []

    def fake_http(url, dest, timeout=30, progress=None):
        progress(1, 2)
        raise OSError("stop")
    monkeypatch.setattr(updater, "_http_download", fake_http)
    assert updater.download_update(_info(), str(tmp_path / "x.zip"), progress=lambda d, t: calls.append((d, t))) is False
    assert calls == [(1, 2)]
