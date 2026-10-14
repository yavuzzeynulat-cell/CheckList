"""3. adim: sonuc. Uc sayi, eksiklerin onizlemesi, Excel kendiliginden kaydedilir."""
import os
import subprocess
import tkinter as tk

import detect
import output
import theme
import ui
from steps import Step

PREVIEW = 300            # onizlemede en cok satir; tamami Excel'de


class ResultStep(Step):
    key = "result"
    title = "Result"

    def __init__(self, opener=None):
        self.opener = opener or os.startfile
        self.view = "missing"
        self.error = ""

    def build(self, frame, ctx):
        super().build(frame, ctx)
        s = ctx.s
        body = self.page("Result", "")
        bar = self.action_bar()
        self.open_btn = ui.Button(bar, "Open Excel", self.open_excel, kind="primary", size=11, padx=s(22), pady=s(10))
        self.open_btn.pack(side="right")
        self.folder_btn = ui.Button(bar, "Show in folder", self.open_folder, pady=s(10))
        self.folder_btn.pack(side="right", padx=(0, s(10)))
        self.again_btn = ui.Button(bar, "Start over", self.start_over, pady=s(10))
        self.again_btn.pack(side="right", padx=(0, s(10)))

        tiles = tk.Frame(body, bg=theme.PAPER)
        tiles.pack(fill="x")
        self.tiles = {}
        for i, (key, label, color, bg) in enumerate((("kept", "RIAs compared", theme.INK, theme.SHEET),
                                                     ("has", "Have a checklist", theme.GREEN, theme.GREEN_BG),
                                                     ("missing", "Missing a checklist", theme.ORANGE, theme.ORANGE_BG))):
            tiles.columnconfigure(i, weight=1, uniform="t")
            t = tk.Frame(tiles, bg=bg, highlightthickness=1, highlightbackground=color if key != "kept" else theme.RULE)
            t.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else s(8), 0))
            ui.eyebrow(t, label, bg=bg, fg=color if key != "kept" else theme.MUTED).pack(
                fill="x", padx=s(18), pady=(s(14), 0))
            n = tk.Label(t, text="0", bg=bg, fg=color, font=theme.mono(30, "SemiBold"), anchor="w")
            n.pack(fill="x", padx=s(16), pady=(0, s(2)))
            sub = tk.Label(t, text="", bg=bg, fg=theme.MUTED, font=theme.font(8), anchor="w")
            sub.pack(fill="x", padx=s(18), pady=(0, s(12)))
            self.tiles[key] = (n, sub)
        self.notes = tk.Label(body, text="", bg=theme.PAPER, fg=theme.MUTED, font=theme.font(9), anchor="w")
        self.notes.pack(fill="x", pady=(s(8), s(8)))

        c = ui.card(body)
        c.pack(fill="both", expand=True)
        head = tk.Frame(c, bg=theme.SHEET)
        head.pack(fill="x", padx=s(18), pady=(s(10), s(6)))
        self.tab_lbls = {}
        for key in ("missing", "has"):
            lb = tk.Label(head, text="", bg=theme.SHEET, font=theme.font(9, "Semibold"), cursor="hand2")
            lb.pack(side="left", padx=(0, s(18)))
            lb.bind("<Button-1>", lambda e, k=key: self.set_view(k))
            self.tab_lbls[key] = lb
        tk.Frame(c, bg=theme.RULE, height=1).pack(fill="x")
        self.list = ui.Scroll(c)
        self.list.pack(fill="both", expand=True, padx=s(18), pady=(s(4), s(8)))

    # --- islemler -------------------------------------------------------------
    def show(self):
        session = self.ctx.session
        if session.result is None and session.ready:
            session.run()
        if session.result is not None and session.out_path is None:
            try:
                session.save()
                self.error = ""
            except output.OutputError as e:
                self.error = str(e)
        self._redraw()

    def set_view(self, key):
        self.view = key
        self._redraw()

    def open_excel(self):
        p = self.ctx.session.out_path
        if self.error:
            self.show()
            return
        if p and p.exists():
            self.opener(str(p))

    def open_folder(self):
        p = self.ctx.session.out_path
        if p and p.exists():
            subprocess.Popen(["explorer", "/select,", str(p)])

    def start_over(self):
        self.ctx.session.clear()
        self.ctx.go("files")

    # --- cizim ----------------------------------------------------------------
    def _rows(self):
        res = self.ctx.session.result
        h = res.ria_header
        i, t = h.index(detect.RIA_KEY), (h.index("Document Title") if "Document Title" in h else None)
        if self.view == "missing":
            return [(r[i], r[t] if t is not None else "", "") for r in res.missing]
        ch = res.check_header
        ci = ch.index("Task Number") if "Task Number" in ch else None
        si = ch.index("Status") if "Status" in ch else None
        return [(r[i], r[t] if t is not None else "",
                 " · ".join(str(c[k]) for k in (ci, si) if k is not None and c[k] not in (None, "")))
                for r, c in res.matched]

    def _redraw(self):
        if not hasattr(self, "tiles"):
            return
        s, session = self.ctx.s, self.ctx.session
        res = session.result
        for w in self.list.body.winfo_children():
            w.destroy()
        has_res = res is not None
        for b in (self.open_btn, self.folder_btn):
            b.set_enabled(has_res and (session.out_path is not None or bool(self.error)))
        self.open_btn.set_text("Try again" if self.error else "Open Excel")
        if not has_res:
            self.sub.config(text="Drop a RIA list and a checklist first.")
            for n, sub in self.tiles.values():
                n.config(text="–")
                sub.config(text="")
            self.notes.config(text="")
            self.sum1.config(text="")
            self.sum2.config(text="")
            for lb in self.tab_lbls.values():
                lb.config(text="")
            return
        self.sub.config(text="RIA list compared with the checklist by RIA number "
                             "(Document Number = Related RIA).")
        missing = len(res.missing)
        vals = {"kept": (res.kept, f"of {ui.plural(res.total, 'RIA')} in the files"),
                "has": (res.with_checklist, ui.plural(len(res.matched), "checklist row")),
                "missing": (missing, "listed in the Excel")}
        for key, (n, sub) in self.tiles.items():
            v, text = vals[key]
            n.config(text=f"{v:,}")
            sub.config(text=text)
        notes = []
        if res.removed:
            notes.append(f"{ui.plural(sum(res.removed.values()), 'RIA')} left out by the filter")
        if res.duplicates:
            notes.append(f"{ui.plural(res.duplicates, 'RIA')} in more than one file (counted once)")
        if res.rejected:
            notes.append(f"{ui.plural(res.rejected, 'rejected checklist')} ignored")
        if res.orphans:
            notes.append(f"{ui.plural(res.orphans, 'checklist')} for RIAs not compared")
        self.notes.config(text="  ·  ".join(notes))
        for key, label, n in (("missing", "Missing a checklist", missing), ("has", "Have a checklist", len(res.matched))):
            on = key == self.view
            color = theme.ORANGE if key == "missing" else theme.GREEN
            self.tab_lbls[key].config(text=f"{label}  {n:,}", fg=color if on else theme.FAINT,
                                      font=theme.font(9, "Semibold underline" if on else "Semibold"))
        rows = self._rows()
        for num, title, extra in rows[:PREVIEW]:
            r = tk.Frame(self.list.body, bg=theme.SHEET)
            r.pack(fill="x")
            tk.Label(r, text=str(num), bg=theme.SHEET, fg=theme.INK, font=theme.mono(9), width=34,
                     anchor="w").pack(side="left", pady=s(3))
            if extra:
                tk.Label(r, text=extra, bg=theme.SHEET, fg=theme.GREEN, font=theme.mono(8)).pack(side="right")
            tk.Label(r, text=ui.fit_text(str(title or ""), theme.font(9), s(470)), bg=theme.SHEET,
                     fg=theme.MUTED, font=theme.font(9), anchor="w").pack(side="left", fill="x", expand=True)
            tk.Frame(self.list.body, bg=theme.RULE, height=1).pack(fill="x")
        if len(rows) > PREVIEW:
            tk.Label(self.list.body, text=f"+{len(rows) - PREVIEW:,} more in the Excel", bg=theme.SHEET,
                     fg=theme.FAINT, font=theme.font(9), anchor="w").pack(fill="x", pady=s(6))
        if not rows:
            tk.Label(self.list.body, text="Nothing here — every compared RIA has a checklist." if self.view == "missing"
                     else "No RIA has a checklist yet.", bg=theme.SHEET, fg=theme.FAINT,
                     font=theme.font(9), anchor="w").pack(fill="x", pady=s(6))
        self.list.top()
        if self.error:
            self.sum1.config(text="Could not save the Excel", fg=theme.RED)
            self.sum2.config(text=self.error)
        elif session.out_path:
            self.sum1.config(text=f"Saved  ·  {session.out_path.name}", fg=theme.INK)
            self.sum2.config(text=ui.fit_text(str(session.out_path.parent), theme.font(9), s(520)))
