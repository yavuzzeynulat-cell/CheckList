"""1. adim: Excel'leri birak. Hangisi RIA listesi, hangisi checklist --
program basliktan anlar ve iki sutuna ayirir (kullanici 2026-10-14)."""
import threading
import tkinter as tk
from tkinter import filedialog

import detect
import dnd
import theme
import ui
from steps import Step


class FilesStep(Step):
    key = "files"
    title = "Files"

    def __init__(self, ask_files=None):
        self.ask_files = ask_files
        self.busy = False
        self._hook = None

    def build(self, frame, ctx):
        super().build(frame, ctx)
        s = ctx.s
        body = self.page("Drop your Excel files",
                         "RIA lists and checklists together, in any order. "
                         "CheckList reads the columns and sorts them out.")
        bar = self.action_bar()
        self.next_btn = ui.Button(bar, "Continue to filter  →", lambda: ctx.go("filter"), kind="primary", size=11,
                                  padx=s(22), pady=s(10))
        self.next_btn.pack(side="right")
        self.clear_btn = ui.Button(bar, "Clear", self.clear, pady=s(10))
        self.clear_btn.pack(side="right", padx=(0, s(10)))

        self.zone = tk.Canvas(body, bg=theme.PAPER, highlightthickness=0, bd=0, height=s(150), cursor="hand2")
        self.zone.pack(fill="x")
        self.zone.bind("<Configure>", lambda e: self._draw_zone())
        self.zone.bind("<Button-1>", lambda e: self.browse())

        self.others = tk.Frame(body, bg=theme.PAPER)
        self.others.pack(fill="x", side="bottom")
        cols = tk.Frame(body, bg=theme.PAPER)
        cols.pack(fill="both", expand=True, pady=(s(16), 0))
        cols.columnconfigure(0, weight=1, uniform="c")
        cols.columnconfigure(1, weight=1, uniform="c")
        cols.rowconfigure(0, weight=1)
        self.lists = {}
        for i, (kind, head, color) in enumerate(((detect.RIA, "RIA lists", theme.INK),
                                                  (detect.CHECKLIST, "Checklists", theme.GREEN))):
            c = ui.card(cols)
            c.grid(row=0, column=i, sticky="nsew", padx=(0, s(8)) if i == 0 else (s(8), 0))
            top = tk.Frame(c, bg=theme.SHEET)
            top.pack(fill="x", padx=s(18), pady=(s(14), s(6)))
            tk.Frame(top, bg=color, width=s(8), height=s(8)).pack(side="left", padx=(0, s(8)))
            ui.eyebrow(top, head).pack(side="left")
            cnt = tk.Label(top, text="", bg=theme.SHEET, fg=theme.MUTED, font=theme.mono(8))
            cnt.pack(side="right")
            sc = ui.Scroll(c)
            sc.pack(fill="both", expand=True, padx=s(18), pady=(0, s(12)))
            self.lists[kind] = (sc, cnt)
        self._install_drop()
        self.refresh()

    # --- birakma / secme ----------------------------------------------------
    def _install_drop(self):
        root = self.ctx.root
        try:
            root.update_idletasks()
            self._hook = dnd.install(root)
        except Exception:
            self._hook = None
        if self._hook is not None:
            self._poll()

    def _poll(self):
        try:
            for paths in self._hook.drain():
                self.ctx.go(self.key)
                self.add(paths)
            self.ctx.root.after(150, self._poll)
        except tk.TclError:
            pass

    def browse(self):
        if self.busy:
            return
        if self.ask_files:
            paths = self.ask_files()
        else:
            paths = filedialog.askopenfilenames(parent=self.ctx.root, title="Choose RIA lists and checklists",
                                                filetypes=[("Excel", "*.xlsx *.xlsm")])
        if paths:
            self.add(paths)

    def add(self, paths, wait=False):
        """Dosyalari arka planda okur (buyuk DataGrid birkac saniye surebilir)."""
        session = self.ctx.session
        todo = [p for p in detect.expand_drop(paths) if detect.norm(p) not in session.tables]
        if not todo:
            return
        self.busy = True
        self.refresh()
        box = {}

        def work():
            box["tables"] = {detect.norm(p): detect.read(p) for p in todo}
        th = threading.Thread(target=work, daemon=True)
        th.start()
        if wait:                       # testler
            th.join()

        def done():
            if th.is_alive():
                self.ctx.root.after(60, done)
                return
            tables = box.get("tables", {})
            session.add(todo, read=lambda p: tables[detect.norm(p)])
            self.busy = False
            self.refresh()
        done()

    def remove(self, path):
        self.ctx.session.remove(path)
        self.refresh()

    def clear(self):
        self.ctx.session.clear()
        self.refresh()

    def show(self):
        self.refresh()

    # --- cizim ----------------------------------------------------------------
    def _draw_zone(self):
        cv, s = self.zone, self.ctx.s
        cv.delete("all")
        W, H = cv.winfo_width(), cv.winfo_height()
        if W <= 1:
            return
        cv.create_rectangle(1, 1, W - 2, H - 2, fill=theme.SHEET, outline=theme.RULE_DARK, dash=(6, 4))
        cx = W / 2
        if self.busy:
            cv.create_text(cx, H / 2, text="Reading files…", fill=theme.MUTED, font=theme.font(12, "Semibold"))
            return
        # kucuk belge ikonu: iki kagit ust uste
        x, y = cx - s(14), s(30)
        cv.create_rectangle(x + s(8), y - s(6), x + s(36), y + s(28), fill=theme.SHEET_HI, outline=theme.RULE_DARK)
        cv.create_rectangle(x, y, x + s(28), y + s(34), fill=theme.SHEET, outline=theme.INK)
        for k in (10, 17, 24):
            cv.create_line(x + s(6), y + s(k), x + s(22), y + s(k), fill=theme.RULE_DARK)
        cv.create_text(cx, s(92), text="Drop Excel files here", fill=theme.INK, font=theme.font(13, "Semibold"))
        cv.create_text(cx, s(116), text="or click to browse  ·  folders work too", fill=theme.MUTED,
                       font=theme.font(9))

    def _row(self, parent, t):
        s = self.ctx.s
        row = tk.Frame(parent, bg=theme.SHEET)
        row.pack(fill="x", pady=(0, s(6)))
        tk.Frame(row, bg=theme.RULE, height=1).pack(fill="x", side="bottom", pady=(s(6), 0))
        x = tk.Label(row, text="✕", bg=theme.SHEET, fg=theme.FAINT, font=theme.font(9), cursor="hand2")
        x.pack(side="right", padx=(s(8), 0))
        x.bind("<Button-1>", lambda e, p=t.path: self.remove(p))
        x.bind("<Enter>", lambda e: x.config(fg=theme.RED))
        x.bind("<Leave>", lambda e: x.config(fg=theme.FAINT))
        tk.Label(row, text=ui.plural(len(t.rows), "row"), bg=theme.SHEET, fg=theme.MUTED,
                 font=theme.mono(8)).pack(side="right")
        tk.Label(row, text=ui.fit_text(t.path.name, theme.font(10), s(330)), bg=theme.SHEET, fg=theme.INK,
                 font=theme.font(10), anchor="w").pack(side="left", fill="x", expand=True)

    def refresh(self):
        if not hasattr(self, "lists"):
            return
        session, s = self.ctx.session, self.ctx.s
        self._draw_zone()
        for kind, (sc, cnt) in self.lists.items():
            for w in sc.body.winfo_children():
                w.destroy()
            tables = session.of(kind)
            for t in tables:
                self._row(sc.body, t)
            if not tables:
                tk.Label(sc.body, text="None yet", bg=theme.SHEET, fg=theme.FAINT, font=theme.font(9),
                         anchor="w").pack(fill="x", pady=s(4))
            cnt.config(text=ui.plural(sum(len(t.rows) for t in tables), "row") if tables else "")
        for w in self.others.winfo_children():
            w.destroy()
        for t in session.others:
            row = tk.Frame(self.others, bg=theme.ORANGE_BG, highlightthickness=1, highlightbackground=theme.ORANGE)
            row.pack(fill="x", pady=(s(8), 0))
            tk.Label(row, text=f"Not used: {t.path.name}  —  {t.error}", bg=theme.ORANGE_BG, fg=theme.ORANGE,
                     font=theme.font(9, "Semibold"), anchor="w").pack(side="left", padx=s(12), pady=s(5))
            x = tk.Label(row, text="✕", bg=theme.ORANGE_BG, fg=theme.ORANGE, cursor="hand2", font=theme.font(9))
            x.pack(side="right", padx=s(10))
            x.bind("<Button-1>", lambda e, p=t.path: self.remove(p))
        r, c = session.rias, session.checklists
        self.next_btn.set_enabled(bool(r) and not self.busy)
        self.clear_btn.set_enabled(bool(session.tables) and not self.busy)
        if not session.tables:
            self.sum1.config(text="No files yet")
            self.sum2.config(text="Download the RIA list and the checklist from EDMS, then drop them above.")
        else:
            self.sum1.config(text=f"{ui.plural(len(r), 'RIA list')}  ·  {ui.plural(len(c), 'checklist')}")
            if not r:
                hint = "A RIA list is needed — it has Document Number and Document Title columns."
            elif not c:
                hint = "No checklist yet — without one, every RIA will be listed as missing."
            else:
                hint = "Ready. Next: choose which RIAs to compare."
            self.sum2.config(text=hint)
