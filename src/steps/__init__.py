"""Adim kaydi. Yeni adim: bu klasore bir dosya + all_steps()'e bir satir."""
import tkinter as tk

import theme


class Step:
    key = ""
    title = ""
    bottom = False           # True: sekme sagda, numarasiz (Settings)

    def build(self, frame, ctx):
        """Bir kez: frame'in icini kurar."""
        self.frame, self.ctx = frame, ctx

    def show(self):
        """Adim her gorunur oldugunda."""

    def hide(self):
        """Baska adima gecilirken."""

    # ortak parcalar
    def page(self, title, sub):
        """Baslik + aciklama; altindaki icerik alani doner."""
        s = self.ctx.s
        top = tk.Frame(self.frame, bg=theme.PAPER)
        top.pack(fill="x", padx=s(32), pady=(s(22), s(14)))
        tk.Label(top, text=title, bg=theme.PAPER, fg=theme.INK, font=theme.font(18, "Semibold"),
                 anchor="w").pack(fill="x")
        self.sub = tk.Label(top, text=sub, bg=theme.PAPER, fg=theme.MUTED, font=theme.font(10), anchor="w",
                            justify="left")
        self.sub.pack(fill="x", pady=(s(2), 0))
        self._bar = tk.Frame(self.frame, bg=theme.PAPER)
        self._bar.pack(fill="x", side="bottom", padx=s(32), pady=(s(14), s(18)))
        body = tk.Frame(self.frame, bg=theme.PAPER)
        body.pack(fill="both", expand=True, padx=s(32))
        return body

    def action_bar(self):
        """Altta: solda ozet, sagda dugmeler (page()'den sonra)."""
        bar = self._bar
        left = tk.Frame(bar, bg=theme.PAPER)
        left.pack(side="left", fill="x", expand=True)
        self.sum1 = tk.Label(left, text="", bg=theme.PAPER, fg=theme.INK, font=theme.font(11, "Semibold"), anchor="w")
        self.sum1.pack(fill="x")
        self.sum2 = tk.Label(left, text="", bg=theme.PAPER, fg=theme.MUTED, font=theme.font(9), anchor="w",
                             justify="left")
        self.sum2.pack(fill="x")
        return bar


def all_steps():
    from steps.files import FilesStep
    from steps.filter import FilterStep
    from steps.prefs import SettingsStep
    from steps.result import ResultStep
    return [FilesStep(), FilterStep(), ResultStep(), SettingsStep()]
