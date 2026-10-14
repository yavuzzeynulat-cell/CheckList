"""Parca filtresi kutucuklari: her parca bir satir, degerler akarak dizilir.

Handover'daki secim mantigi (tikli = tutulur, adet yaninda), bu temanin
gorunumuyle: keskin kenar, numaralar es aralikli yazida. Filtre adimi ve
Settings > Default filter ayni sinifi kullanir.
"""
import tkinter as tk
import tkinter.font as tkfont

import riafilter
import theme
import ui

CHIP_H = 30
LABEL_W = 120
GAP = 8


class PartChips(tk.Canvas):
    def __init__(self, parent, S, values, is_on, toggle, set_all, count=None, bg=theme.SHEET):
        """values(part) -> [deger]; count(part, deger) -> int | None."""
        super().__init__(parent, bg=bg, highlightthickness=0, bd=0, height=10)
        self.S, self.values, self.is_on, self.toggle, self.set_all, self.count = S, values, is_on, toggle, set_all, count
        self.bg = bg
        self.f_val = tkfont.Font(font=theme.mono(10))
        self.f_cnt = tkfont.Font(font=theme.mono(8))
        self._width = 0
        self.bind("<Configure>", self._on_size)

    def s(self, v):
        return v * self.S

    def _on_size(self, e):
        if e.width != self._width:
            self._width = e.width
            self.redraw()

    def _chip_w(self, value, n):
        w = self.s(10) + self.s(14) + self.s(8) + self.f_val.measure(value) + self.s(12)
        if n is not None:
            w += self.f_cnt.measure(f"{n:,}") + self.s(8)
        return w

    def parts(self):
        return [p for p in riafilter.PARTS if self.values(p)]

    def redraw(self):
        self.delete("all")
        s, W = self.s, max(self._width, self.winfo_width())
        if W <= 1:
            return
        parts = self.parts()
        if not parts:
            self.create_text(W / 2, s(30), text="No RIA list yet — drop one on the Files step.",
                             fill=theme.FAINT, font=theme.font(10))
            self.config(height=s(60))
            return
        y = s(4)
        x0 = s(LABEL_W)
        for i, part in enumerate(parts):
            if i:
                self.create_line(0, y - s(10), W, y - s(10), fill=theme.RULE)
            self.create_text(0, y + s(8), text=part.upper(), anchor="w", fill=theme.INK_SOFT,
                             font=theme.font(8, "Semibold"))
            self._all_none(0, y + s(26), part)
            cx = x0
            for value in self.values(part):
                n = self.count(part, value) if self.count else None
                w = self._chip_w(value, n)
                if cx + w > W and cx > x0:
                    cx, y = x0, y + s(CHIP_H) + s(GAP)
                self._chip(cx, y, value, n, part)
                cx += w + s(GAP)
            y += s(CHIP_H) + s(22)
        self.config(height=max(s(40), y - s(16)))

    def _all_none(self, x, y, part):
        vals = self.values(part)
        off = sum(1 for v in vals if not self.is_on(part, v))
        for label, on, active in (("All", True, off == 0), ("None", False, off == len(vals))):
            t = self.create_text(x, y, text=label, anchor="w", font=theme.font(8, "Semibold" if active else ""),
                                 fill=theme.INK if active else theme.FAINT)
            self.tag_bind(t, "<Button-1>", lambda e, p=part, v=on: self.set_all(p, v))
            self.tag_bind(t, "<Enter>", lambda e: self.config(cursor="hand2"))
            self.tag_bind(t, "<Leave>", lambda e: self.config(cursor=""))
            x = self.bbox(t)[2] + self.s(10)

    def _chip(self, x, y, value, n, part):
        s = self.s
        on = self.is_on(part, value)
        w, h = self._chip_w(value, n), s(CHIP_H)
        tag = f"chip:{part}:{value}"
        self.create_rectangle(x, y, x + w, y + h, fill=theme.SHEET if on else theme.SHEET_HI,
                              outline=theme.INK if on else theme.RULE, tags=tag)
        box = s(14)
        ui.checkbox(self, x + s(10), y + (h - box) / 2, box, on, tags=tag)
        tx = x + s(10) + box + s(8)
        self.create_text(tx, y + h / 2, text=value, anchor="w", font=self.f_val,
                         fill=theme.INK if on else theme.FAINT, tags=tag)
        if n is not None:
            self.create_text(x + w - s(10), y + h / 2, text=f"{n:,}", anchor="e", font=self.f_cnt,
                             fill=theme.MUTED if on else theme.FAINT, tags=tag)
        self.tag_bind(tag, "<Button-1>", lambda e: self.toggle(part, value))
        self.tag_bind(tag, "<Enter>", lambda e: self.config(cursor="hand2"))
        self.tag_bind(tag, "<Leave>", lambda e: self.config(cursor=""))
