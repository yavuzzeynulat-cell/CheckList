"""Renkler ve fontlar. Handover'in koyu/yuvarlak/parlayan temasinin tersi
(kullanici 2026-10-14: "temasi baska olsun ama guzel olsun"): kagit zemin,
keskin koseler, ince cizgiler -- bir denetim formu gibi. Renk yalniz anlam
tasir: yesil = checklist'i var, turuncu = eksik.
"""
import ctypes

PAPER = "#f3f0e8"        # pencere zemini
SHEET = "#fffdf8"        # kart
SHEET_HI = "#f8f5ee"     # kart ustunde secili/hover
RULE = "#dcd6ca"         # ince cizgi
RULE_DARK = "#b9b2a4"
INK = "#1d2420"          # ana yazi, birincil dugme
INK_SOFT = "#3a423d"
MUTED = "#6c716a"
FAINT = "#a19d93"
GREEN = "#2b8a3e"        # checklist'i olanlar
GREEN_BG = "#e6f2e6"
ORANGE = "#d9480f"       # olmasi gerekenler
ORANGE_BG = "#fbe9df"
RED = "#c92a2a"
RED_BG = "#fbe4e4"
FONT = "Segoe UI"
MONO = "Cascadia Mono"
APP_ID = "Yavuz.CheckList"


def font(size, weight=""):
    return (FONT + (" " + weight if weight else ""), size)


def mono(size, weight=""):
    return (MONO + (" " + weight if weight else ""), size)


def pick_mono():
    """Tk kurulduktan sonra: Cascadia Mono Windows 10'da her makinede yok."""
    global MONO
    try:
        import tkinter.font as tkfont
        fams = set(tkfont.families())
        MONO = next((f for f in ("Cascadia Mono", "Consolas") if f in fams), "Courier New")
    except Exception:
        pass


def enable_dpi():
    """Tk() olusmadan ONCE: DPI-aware olmazsa Windows pencereyi bulaniklastirir."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass
    try:  # gorev cubugunda python ikonu yerine kendi ikonumuz
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass


def scale_of(root):
    return root.winfo_fpixels("1i") / 96
