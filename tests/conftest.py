import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "build"))
sys.path.insert(0, ROOT)

import tkinter as tk

import pytest

_ROOT = []


@pytest.fixture
def tk_root():
    """Surec basina TEK Tk (Windows'ta art arda Tk() ara sira init.tcl okuyamiyor)."""
    if not _ROOT:
        import main
        r = main.new_root()
        r.withdraw()
        _ROOT.append(r)
    r = _ROOT[0]
    tk._default_root = r
    yield r
    for w in r.winfo_children():
        w.destroy()
    for seq in r.bind():
        r.unbind(seq)
    r.withdraw()
    r.update()


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path, monkeypatch):
    """Testler kullanicinin gercek ayarlarini okuyup yazmasin."""
    import settings
    monkeypatch.setattr(settings, "PATH", tmp_path / "settings.json")
    # "Hicbir sey kapali degil" kayitli; varsayilan filtre test_settings'te ayrica.
    settings.save_exclude({})
