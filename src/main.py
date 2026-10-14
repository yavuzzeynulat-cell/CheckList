"""Uygulama girisi (src/ icinde, guncellenebilir): acilis -> guncelleme kontrolu -> pencere."""
import threading
import tkinter as tk
from pathlib import Path

import shell
import splash
import steps
import theme
import ui

INSTANCE = "Local\\CheckList.Yavuz"
UPDATE_WAIT_MS = 6000


def read_version():
    try:
        return (Path(__file__).parent / "version.txt").read_text(encoding="utf-8").strip()
    except OSError:
        return "0.0.0"


def single_instance(name=INSTANCE, wait_ms=4000):
    """Tek kopya kilidi (adli semafor, Handover'daki gibi). Alinamazsa None."""
    import ctypes
    k = ctypes.windll.kernel32
    k.CreateSemaphoreW.restype = ctypes.c_void_p
    h = k.CreateSemaphoreW(None, 1, 1, name)
    if not h:
        return True
    if k.WaitForSingleObject(ctypes.c_void_p(h), int(wait_ms)) == 0:
        return h
    k.CloseHandle(ctypes.c_void_p(h))
    return None


def release_instance(h):
    import ctypes
    if h and h is not True:
        k = ctypes.windll.kernel32
        k.ReleaseSemaphore(ctypes.c_void_p(h), 1, None)
        k.CloseHandle(ctypes.c_void_p(h))


def _focus_existing():
    import ctypes
    u = ctypes.windll.user32
    h = u.FindWindowW(None, "CheckList")
    if h:
        u.ShowWindow(h, 9)
        u.SetForegroundWindow(h)


def new_root(tries=3, delay=0.3):
    """Tk() ara sira init.tcl okuyamiyor (Handover'da olculdu); tekrar denemek yetiyor."""
    import time
    for i in range(tries):
        try:
            return tk.Tk()
        except tk.TclError:
            if i == tries - 1:
                raise
            time.sleep(delay)


def _start_update_check():
    box = {"done": False, "info": None}

    def work():
        try:
            import updater
            box["info"] = updater.check_for_update(timeout=5)
        except Exception:
            pass
        box["done"] = True
    threading.Thread(target=work, daemon=True).start()
    return box


def after_splash(box, waited_ms):
    """'wait' | 'update' | 'open'. Yeni surum varsa pencere acilmaz
    (guncellemeyen kullanamasin, Handover'daki karar)."""
    if box["done"]:
        return "update" if box["info"] else "open"
    return "wait" if waited_ms < UPDATE_WAIT_MS else "open"


def _update_window(root, version):
    """Guncelleme sirasinda: kart + ilerleme cizgisi + MB."""
    S = theme.scale_of(root)

    def s(v):
        return round(v * S)
    W, H = s(440), s(130)
    win = tk.Toplevel(root)
    win.overrideredirect(True)
    win.attributes("-topmost", True)
    win.geometry(f"{W}x{H}+{(win.winfo_screenwidth() - W) // 2}+{(win.winfo_screenheight() - H) // 2}")
    cv = tk.Canvas(win, width=W, height=H, bg=theme.PAPER, highlightthickness=1,
                   highlightbackground=theme.RULE_DARK, bd=0)
    cv.pack()
    P = s(26)
    cv.create_text(P, s(34), anchor="w", text="Updating CheckList", fill=theme.INK, font=theme.font(13, "Semibold"))
    cv.create_text(P, s(58), anchor="w", text=f"Version {version}  ·  opens again by itself", fill=theme.MUTED,
                   font=theme.font(9))
    y = s(86)
    cv.create_line(P, y, W - P, y, fill=theme.RULE, width=s(3))
    bar = cv.create_line(P, y, P, y, fill=theme.ORANGE, width=s(3))
    status = cv.create_text(P, s(108), anchor="w", text="Connecting…", fill=theme.MUTED, font=theme.font(8))
    pct = cv.create_text(W - P, s(108), anchor="e", text="", fill=theme.INK, font=theme.mono(8))

    def progress(done, total):
        mb = 2 ** 20
        if total:
            f = min(1.0, done / total)
            cv.coords(bar, P, y, P + (W - 2 * P) * f, y)
            cv.itemconfig(status, text=f"Downloading…  {done / mb:.1f} of {total / mb:.1f} MB")
            cv.itemconfig(pct, text=f"{round(100 * f)}%")
        else:
            cv.itemconfig(status, text=f"Downloading…  {done / mb:.1f} MB")
        try:
            win.update()
        except tk.TclError:
            pass
    win.update()
    return win, progress


def _forced_update(root, info):
    from tkinter import messagebox
    import updater
    win, progress = _update_window(root, info.version)
    try:
        ok = updater.run_update_flow(info, parent_window=win, progress=progress)
    except SystemExit:
        raise
    except Exception:
        ok = False
    if not ok:
        try:
            win.destroy()
        except tk.TclError:
            pass
        messagebox.showerror("Update required",
                             "CheckList must be updated to keep working, but the update could not be installed.\n\n"
                             "Check the internet connection and open CheckList again.")
        root.destroy()


def main():
    global _instance
    _instance = single_instance()
    if _instance is None:
        _focus_existing()
        return
    try:
        _run()
    except BaseException:
        # launcher eski surume donup main()'i ayni surecte yeniden cagirabilir
        release_instance(_instance)
        _instance = None
        raise


def _run():
    theme.enable_dpi()
    root = new_root()
    root.withdraw()
    ui.set_icon(root)
    box = _start_update_check()
    state = {"since": None, "action": None, "sh": None}

    def ready():
        import time
        state["since"] = state["since"] or time.monotonic()
        action = after_splash(box, (time.monotonic() - state["since"]) * 1000)
        if action == "wait":
            return False
        if action == "open":
            state["sh"] = shell.Shell(root, steps.all_steps(), version=read_version())
        state["action"] = action
        return True

    def done():
        if state["action"] == "update":
            return _forced_update(root, box["info"])
        state["sh"].show()

    splash.play(root, done, ready=ready)
    root.mainloop()


def selftest():
    """Tum modulleri yukle, kabugu gizli kur, kapat. Hata = istisna."""
    import compare, detect, dnd, output, updater  # noqa: F401,E401
    root = new_root()
    root.withdraw()
    prev, tk._default_root = tk._default_root, root
    try:
        ui.set_icon(root)
        shell.Shell(root, steps.all_steps(), version=read_version())
        root.update()
    finally:
        root.destroy()
        tk._default_root = prev if prev is not root else None
    return 0


if __name__ == "__main__":
    main()
