"""Kucuk arac takimi: dugme, kart, kaydirilan alan, ikon. Keskin koseli,
ince cizgili (theme.py); Tk'nin kendi dikdortgenleri net cikiyor, sprite gerekmiyor."""
import tkinter as tk

from PIL import Image, ImageDraw

import theme

SS = 4


def rgb(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def mix(c1, c2, t):
    t = max(0.0, min(1.0, t))
    a, b = rgb(c1), rgb(c2)
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def animate(widget, dur_ms, fn, done=None):
    """fn(k) k: 0..1, ~60 fps. Bitince done()."""
    t0 = widget.tk.call("clock", "milliseconds")

    def step():
        try:
            k = (widget.tk.call("clock", "milliseconds") - t0) / dur_ms
        except tk.TclError:
            return
        fn(min(1.0, k))
        if k < 1:
            widget.after(15, step)
        elif done:
            done()
    step()


def app_icon(n=256):
    """Amblem: koyu kare, ustunde kagit (pano), turuncu tik."""
    big = n * SS
    im = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, big - 1, big - 1), big * 0.16, fill=rgb(theme.INK) + (255,))
    x0, y0, x1, y1 = big * 0.24, big * 0.2, big * 0.76, big * 0.84
    d.rectangle((x0, y0, x1, y1), fill=rgb(theme.SHEET) + (255,))
    d.rectangle((big * 0.39, big * 0.13, big * 0.61, big * 0.25), fill=rgb(theme.RULE_DARK) + (255,))
    w = round(big * 0.035)
    for k in (0.62, 0.72):
        d.line((big * 0.33, big * k, big * 0.67, big * k), fill=rgb(theme.RULE_DARK) + (255,), width=w)
    d.line([(big * 0.33, big * 0.42), (big * 0.44, big * 0.52), (big * 0.66, big * 0.31)],
           fill=rgb(theme.ORANGE) + (255,), width=round(big * 0.07), joint="curve")
    return im.resize((n, n), Image.LANCZOS)


def caption(win, color=None):
    """Windows 11 baslik cubugunu zemin rengine boyar (10'da sessizce gecer)."""
    try:
        import ctypes
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
        r, g, b = rgb(color or theme.PAPER)
        v = ctypes.c_int(r | (g << 8) | (b << 16))
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(v), 4)
        t = ctypes.c_int(0x00202420)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 36, ctypes.byref(t), 4)
    except Exception:
        pass


def set_icon(win):
    from PIL import ImageTk
    root = win._root()
    img = getattr(root, "_checklist_icon", None)
    try:
        if img is None:
            img = root._checklist_icon = ImageTk.PhotoImage(app_icon(64), master=root)
        win.iconphoto(win is root, img)
    except Exception:
        pass


def card(parent, **kw):
    return tk.Frame(parent, bg=theme.SHEET, highlightthickness=1, highlightbackground=theme.RULE, **kw)


def eyebrow(parent, text, bg=theme.SHEET, fg=theme.MUTED):
    """Kucuk, aralikli buyuk harf baslik ('RIA LISTS')."""
    return tk.Label(parent, text=" ".join(text.upper()).replace("   ", "  "), bg=bg, fg=fg,
                    font=theme.font(7, "Semibold"), anchor="w")


class Button(tk.Label):
    """Duz, keskin koseli dugme. kind: primary | ghost | danger."""
    STYLES = {
        "primary": (theme.INK, theme.SHEET, theme.INK_SOFT, theme.INK),
        "ghost": (theme.SHEET, theme.INK, theme.SHEET_HI, theme.RULE_DARK),
        "danger": (theme.SHEET, theme.RED, theme.RED_BG, theme.RED),
    }

    def __init__(self, parent, text, command, kind="ghost", size=10, padx=16, pady=7):
        self.kind, self.command, self.enabled = kind, command, True
        bg, fg, _, line = self.STYLES[kind]
        super().__init__(parent, text=text, bg=bg, fg=fg, font=theme.font(size, "Semibold"), padx=padx, pady=pady,
                         cursor="hand2", highlightthickness=1, highlightbackground=line, highlightcolor=line)
        self.bind("<Enter>", lambda e: self._paint(True))
        self.bind("<Leave>", lambda e: self._paint(False))
        self.bind("<Button-1>", self._click)

    def _paint(self, hover):
        bg, fg, hi, line = self.STYLES[self.kind]
        if not self.enabled:
            self.config(bg=theme.SHEET_HI if self.kind != "primary" else theme.RULE, fg=theme.FAINT,
                        highlightbackground=theme.RULE, cursor="")
            return
        self.config(bg=hi if hover else bg, fg=fg, highlightbackground=line, cursor="hand2")

    def _click(self, e=None):
        if self.enabled and self.command:
            self.command()

    def set_enabled(self, on):
        self.enabled = bool(on)
        self._paint(False)

    def set_text(self, text):
        self.config(text=text)


class Link(tk.Label):
    def __init__(self, parent, text, command, bg=theme.SHEET, fg=theme.INK, size=9):
        super().__init__(parent, text=text, bg=bg, fg=fg, cursor="hand2", font=theme.font(size, "Semibold underline"))
        self.bind("<Button-1>", lambda e: command())


class Scroll(tk.Frame):
    """Dikey kaydirilan alan; icerik self.body'ye konur. Fare tekerlegi
    yalnizca imlec alanin ustundeyken calisir."""

    def __init__(self, parent, bg=theme.SHEET, **kw):
        super().__init__(parent, bg=bg, **kw)
        self.cv = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.bar = tk.Scrollbar(self, orient="vertical", command=self.cv.yview, width=10)
        self.body = tk.Frame(self.cv, bg=bg)
        self._win = self.cv.create_window(0, 0, window=self.body, anchor="nw")
        self.cv.configure(yscrollcommand=self._on_scroll)
        self.cv.pack(side="left", fill="both", expand=True)
        self.body.bind("<Configure>", lambda e: self._fit())
        self.cv.bind("<Configure>", lambda e: (self.cv.itemconfig(self._win, width=e.width), self._fit()))
        for w in (self.cv, self.body):
            w.bind("<Enter>", lambda e: self.bind_all("<MouseWheel>", self._wheel))
            w.bind("<Leave>", lambda e: self.unbind_all("<MouseWheel>"))

    def _fit(self):
        self.cv.configure(scrollregion=(0, 0, self.body.winfo_reqwidth(), self.body.winfo_reqheight()))

    def _on_scroll(self, a, b):
        self.bar.set(a, b)
        if float(a) <= 0 and float(b) >= 1:
            self.bar.pack_forget()
        elif not self.bar.winfo_ismapped():
            self.bar.pack(side="right", fill="y")

    def _wheel(self, e):
        if self.body.winfo_reqheight() > self.cv.winfo_height():
            self.cv.yview_scroll(-1 if e.delta > 0 else 1, "units")

    def top(self):
        self.cv.yview_moveto(0)


def checkbox(cv, x, y, size, on, color=theme.INK, tags=()):
    """Tuvalde kare kutu; on ise dolu + tik."""
    items = [cv.create_rectangle(x, y, x + size, y + size, outline=color if on else theme.RULE_DARK,
                                 fill=color if on else theme.SHEET, width=1, tags=tags)]
    if on:
        items.append(cv.create_line(x + size * .22, y + size * .52, x + size * .43, y + size * .72,
                                    x + size * .8, y + size * .3, fill=theme.SHEET, width=max(1.5, size * .14),
                                    capstyle="round", joinstyle="round", tags=tags))
    return items


def fit_text(text, font, width):
    """Uzun metni ortadan '…' ile sigdirir."""
    import tkinter.font as tkfont
    f = tkfont.Font(font=font)
    if f.measure(text) <= width:
        return text
    keep = len(text)
    while keep > 4:
        out = text[:keep // 2] + "…" + text[len(text) - keep // 2:]
        if f.measure(out) <= width:
            return out
        keep -= 2
    return "…"


def plural(n, word, many=None):
    return f"{n:,} {word if n == 1 else (many or word + 's')}"
