# -*- mode: python ; coding: utf-8 -*-
# Launcher (onedir). Uygulama kodu EXE'nin yanindaki src/'de; burada gomulu
# olan her sey ancak tam kurulumla degisir. Bu yuzden stdlib'in tamami ve
# kullanilabilecek paketler BASTAN gomulur: ileride src/ yeni bir stdlib
# modulu import ederse kurulum gerekmesin.
import importlib.util
import os
import sys

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
datas, binaries, hidden = [], [], []
secret = os.path.join(ROOT, "license_secret.txt")
if os.path.exists(secret):
    datas.append((secret, "."))
else:
    print("[UYARI] license_secret.txt yok - lisans kapisi KAPALI derlenecek.")
# cryptography: lisans kapisi Ed25519 imzasini dogrular (2026-10-15); yoksa kapi herkesi reddeder.
for pkg in ("openpyxl", "PIL", "et_xmlfile", "cryptography"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hidden += h

SKIP = {"idlelib", "turtledemo", "test", "lib2to3", "ensurepip", "venv", "distutils",
        "antigravity", "this", "pydoc_data", "turtle", "tkinter.test", "unittest.test",
        "curses", "readline", "pty", "tty", "termios", "grp", "pwd", "posix", "resource",
        "fcntl", "nis", "spwd", "crypt", "syslog", "_posixsubprocess", "msilib"}
for name in sorted(sys.stdlib_module_names):
    if name.startswith("_") or name in SKIP:
        continue
    try:
        spec = importlib.util.find_spec(name)
    except Exception:
        continue
    if spec is None:
        continue
    if spec.submodule_search_locations:
        hidden += collect_submodules(name, filter=lambda n: ".test" not in n and ".tests" not in n
                                     and "idle_test" not in n)
    else:
        hidden.append(name)

a = Analysis([os.path.join(ROOT, "launcher.py")], pathex=[ROOT], binaries=binaries, datas=datas,
             hiddenimports=hidden, excludes=["main", "shell", "steps", "splash", "ui", "theme", "updater", "dnd",
                                             "detect", "riafilter", "rules", "compare", "output", "settings"],
             noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="CheckList", console=False, upx=True,
          icon=[os.path.join(ROOT, "assets", "app.ico")])
coll = COLLECT(exe, a.binaries, a.datas, upx=True, name="CheckList")
