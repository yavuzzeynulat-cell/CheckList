"""Pencere: ustte adim sekmeleri (form basligi gibi), altta secili adim.
Handover'da adimlar soldaki koyu kenar cubugundaydi; burada ust serit."""
import tkinter as tk
from dataclasses import dataclass, field

import theme
import ui
from session import Session

WIN_W, WIN_H = 1080, 700


@dataclass
class Ctx:
    root: object
    S: float
    version: str = ""
    session: Session = field(default_factory=Session)
    go: object = None            # go(key): baska adima gec

    def s(self, v):
        return round(v * self.S)


class Shell:
    def __init__(self, root, steps, version):
        self.root, self.steps = root, steps
        self.ctx = Ctx(root=root, S=theme.scale_of(root), version=version)
        self.ctx.go = self.select
        s = self.ctx.s
        theme.pick_mono()
        W, H = s(WIN_W), s(WIN_H)
        root.title("CheckList")
        root.geometry(f"{W}x{H}+{(root.winfo_screenwidth() - W) // 2}+{(root.winfo_screenheight() - H) // 2}")
        root.minsize(s(900), s(600))
        root.configure(bg=theme.PAPER)
        self._head()
        tk.Frame(root, bg=theme.RULE, height=1).pack(fill="x")
        self.stage = tk.Frame(root, bg=theme.PAPER)
        self.stage.pack(fill="both", expand=True)
        self._foot()
        self.frames = {}
        self.active = None
        for st in steps:
            f = tk.Frame(self.stage, bg=theme.PAPER)
            f.place(x=0, y=0, relwidth=1, relheight=1)
            st.build(f, self.ctx)
            self.frames[st.key] = f
        self.select(steps[0].key)

    def _head(self):
        s = self.ctx.s
        bar = tk.Frame(self.root, bg=theme.PAPER, height=s(64))
        bar.pack(fill="x")
        bar.pack_propagate(False)
        from PIL import ImageTk
        self._logo = ImageTk.PhotoImage(ui.app_icon(s(30)), master=self.root)
        tk.Label(bar, image=self._logo, bg=theme.PAPER).pack(side="left", padx=(s(28), s(10)))
        tk.Label(bar, text="CheckList", bg=theme.PAPER, fg=theme.INK, font=theme.font(15, "Semibold")).pack(side="left")
        tk.Frame(bar, bg=theme.RULE, width=1).pack(side="left", fill="y", padx=s(24), pady=s(18))
        self.tabs = {}
        numbered = [st for st in self.steps if not getattr(st, "bottom", False)]
        for st in self.steps:
            right = getattr(st, "bottom", False)
            box = tk.Frame(bar, bg=theme.PAPER, cursor="hand2")
            box.pack(side="right" if right else "left", padx=(0, s(28)) if right else (0, s(26)), fill="y")
            row = tk.Frame(box, bg=theme.PAPER)
            row.pack(expand=True)
            num = None
            if not right:
                num = tk.Label(row, text=f"{numbered.index(st) + 1:02d}", bg=theme.PAPER, font=theme.mono(9))
                num.pack(side="left", padx=(0, s(8)))
            name = tk.Label(row, text=st.title, bg=theme.PAPER, font=theme.font(10, "Semibold"))
            name.pack(side="left")
            line = tk.Frame(box, bg=theme.PAPER, height=s(3))
            line.place(relx=0, rely=1, relwidth=1, anchor="sw")
            for w in (box, row, name) + ((num,) if num else ()):
                w.bind("<Button-1>", lambda e, k=st.key: self.select(k))
                w.configure(cursor="hand2")
            self.tabs[st.key] = (num, name, line)

    def _foot(self):
        s = self.ctx.s
        tk.Frame(self.root, bg=theme.RULE, height=1).pack(fill="x", side="bottom")
        foot = tk.Frame(self.root, bg=theme.PAPER)
        foot.pack(fill="x", side="bottom", before=self.stage)
        tk.Label(foot, text=f"v{self.ctx.version}  ·  by Yavuz Zeynula", bg=theme.PAPER, fg=theme.FAINT,
                 font=theme.font(8)).pack(side="left", padx=s(28), pady=s(6))

    def _mark(self):
        for key, (num, name, line) in self.tabs.items():
            on = self.active is not None and key == self.active.key
            name.config(fg=theme.INK if on else theme.MUTED)
            if num:
                num.config(fg=theme.ORANGE if on else theme.FAINT)
            line.config(bg=theme.INK if on else theme.PAPER)

    def select(self, key):
        st = next((x for x in self.steps if x.key == key), None)
        if st is None:
            return False
        if self.active is not None and self.active is not st:
            self.active.hide()
        self.active = st
        self.frames[key].tkraise()
        self._mark()
        st.show()
        return True

    def show(self):
        self.root.attributes("-alpha", 0.0)
        self.root.deiconify()
        ui.caption(self.root)
        ui.animate(self.root, 220, lambda k: self.root.attributes("-alpha", ui.ease(k)))
        self.root.lift()
        self.root.focus_force()
