"""EXE giris noktasi. EXE'ye GOMULU ve nadiren degisir; uygulamanin kendisi
yanindaki src/ klasorunde yasar ve updater ile guncellenir.

Gorevleri: lisans kapisi, src/main.py'yi yuklemek, yeni kod cokerse
src_backup/'a donup bir kez daha denemek. Baska hicbir sey yapmaz -- burada
bir hata "elle yeniden kur" demektir, bu yuzden kucuk tutulur.

--selftest <klasor>: verilen src'yi yukleyip main.selftest() calistirir
(pencere acmaz, lisans sormaz). Yayinlamadan once yeni kodun bu EXE'de
acildigini kanitlamak icin publish.py kullanir.
"""
import os
import shutil
import sys
import traceback

# --- EXE'ye gomulmesi gereken bagimliliklar ---------------------------------
# src/ ileride bunlari import edebilsin diye burada (PyInstaller analizi icin).
import tkinter  # noqa: F401
import tkinter.filedialog  # noqa: F401
import tkinter.font  # noqa: F401
import tkinter.messagebox  # noqa: F401
import tkinter.ttk  # noqa: F401
import PIL.Image  # noqa: F401
import PIL.ImageDraw  # noqa: F401
import PIL.ImageFilter  # noqa: F401
import PIL.ImageGrab  # noqa: F401
import PIL.ImageTk  # noqa: F401
import openpyxl  # noqa: F401

import license_client

LAUNCHER_VERSION = 1


def _app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _local_version():
    try:
        with open(os.path.join(_app_dir(), "src", "version.txt"), encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return ""


def _purge(src):
    """Onceki denemeden kalan src modullerini unut (geri donus sonrasi temiz yukleme)."""
    root = os.path.normcase(os.path.abspath(src)) + os.sep
    for name, mod in list(sys.modules.items()):
        f = getattr(mod, "__file__", None)
        if f and os.path.normcase(os.path.abspath(f)).startswith(root):
            del sys.modules[name]


def _load(src):
    _purge(src)
    sys.path[:] = [p for p in sys.path if os.path.normcase(p) != os.path.normcase(src)]
    sys.path.insert(0, src)
    import main as app_main
    return app_main


def _rollback():
    app = _app_dir()
    src, backup = os.path.join(app, "src"), os.path.join(app, "src_backup")
    if not os.path.isdir(backup):
        return False
    shutil.rmtree(src, ignore_errors=True)
    os.rename(backup, src)
    return True


def _show_error(message):
    try:
        from tkinter import Tk, messagebox
        r = Tk()
        r.withdraw()
        messagebox.showerror("CheckList - could not start", message)
        r.destroy()
    except Exception:
        try:
            with open(os.path.join(_app_dir(), "launcher_crash.log"), "a", encoding="utf-8") as f:
                f.write(message + "\n---\n")
        except OSError:
            pass


def start(argv):
    os.environ["CHECKLIST_LAUNCHER"] = str(LAUNCHER_VERSION)
    if argv[:1] == ["--selftest"]:
        try:
            return int(_load(os.path.abspath(argv[1])).selftest() or 0)
        except BaseException:
            traceback.print_exc()
            return 1

    license_client.require(version=_local_version())
    src = os.path.join(_app_dir(), "src")
    try:
        _load(src).main()
        return 0
    except SystemExit:
        raise
    except BaseException:
        first = traceback.format_exc()
    if not _rollback():
        _show_error("CheckList could not start and there is no previous version to go back to.\n\n"
                    f"{first}\n\nPlease run the installer again.")
        return 1
    try:
        _load(src).main()
        return 0
    except SystemExit:
        raise
    except BaseException:
        _show_error(f"CheckList could not start (even the previous version).\n\n{first}\n\n{traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    sys.exit(start(sys.argv[1:]))
