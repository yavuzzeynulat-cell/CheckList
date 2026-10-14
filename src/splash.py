"""Acilis karti: kagit zemin, amblem, ad, ince ilerleme cizgisi. Kisa tutuldu;
guncelleme kontrolu bitene (ready) kadar son karede bekler."""
import tkinter as tk

from PIL import ImageTk

import theme
import ui

LW, LH = 460, 250
MIN_MS = 1400
FILL_MS = 200


def play(root, on_done, ready=None, min_ms=MIN_MS):
    S = theme.scale_of(root)

    def s(v):
        return round(v * S)
    W, H = s(LW), s(LH)
    top = tk.Toplevel(root)
    top.overrideredirect(True)
    top.attributes("-topmost", True)
    top.attributes("-alpha", 0.0)
    top.geometry(f"{W}x{H}+{(top.winfo_screenwidth() - W) // 2}+{(top.winfo_screenheight() - H) // 2}")
    cv = tk.Canvas(top, width=W, height=H, bg=theme.PAPER, highlightthickness=1,
                   highlightbackground=theme.RULE_DARK, bd=0)
    cv.pack()
    logo = ImageTk.PhotoImage(ui.app_icon(s(56)), master=top)
    cv.image_refs = [logo]
    cx = W / 2
    cv.create_image(cx, s(66), image=logo)
    cv.create_text(cx, s(124), text="CheckList", fill=theme.INK, font=theme.font(22, "Semibold"))
    cv.create_text(cx, s(152), text="RIA lists against checklists", fill=theme.MUTED, font=theme.font(10))
    by, bx0, bx1 = s(190), cx - s(70), cx + s(70)
    cv.create_line(bx0, by, bx1, by, fill=theme.RULE, width=s(2))
    bar = cv.create_line(bx0, by, bx0, by, fill=theme.ORANGE, width=s(2))
    cv.create_text(cx, s(224), text="Yavuz Zeynula  ·  B E C H T E L  –  E N K A", fill=theme.FAINT,
                   font=theme.font(8))
    st = {"t0": None, "ready_at": None}

    def frame():
        now = root.tk.call("clock", "milliseconds")
        st["t0"] = st["t0"] or now
        ms = now - st["t0"]
        top.attributes("-alpha", ui.ease(ms / 250))
        p = min(0.85, 0.85 * ui.ease(ms / min_ms))
        if ms >= min_ms and st["ready_at"] is None and (ready is None or ready()):
            st["ready_at"] = now
        if st["ready_at"] is not None:
            k = (now - st["ready_at"]) / FILL_MS
            p = 0.85 + 0.15 * min(1.0, k)
            if k >= 1:
                top.destroy()
                on_done()
                return
        cv.coords(bar, bx0, by, bx0 + (bx1 - bx0) * p, by)
        top.after(15, frame)

    top.after(20, frame)
    return top
