"""Daily RIAs: gunun RIA listesini isaretlenebilir saha listesine cevirir.

01-02-03 akisindan bagimsiz (kullanici 2026-10-23: "bu yaptigi isten bagimsiz olacak");
sekmesi sagda, Settings'in yaninda. Dosyalar oturumla ortak: Files'a birakilan RIA
listesi burada da gorunur, buraya birakilan Files'ta da.
Zaman araligi EDMS'te girilip indiriliyor; burada aralik yok, dosyanin hepsi alinir.
RIA parca filtresi Filter adimindakiyle ayni kutucuklar, secimi ayri saklanir
(settings.daily_exclude); Settings'teki kurallar ortak.
"""
import datetime as dt
import os
import subprocess
import threading
import tkinter as tk
from collections import Counter
from tkinter import filedialog

import dailyrias
import detect
import output
import riafilter
import rules as rulemod
import settings
import theme
import ui
from chips import PartChips
from steps import Step


class DailyStep(Step):
    key = "daily"
    title = "Daily RIAs"
    bottom = True

    def __init__(self, opener=None, ask_files=None):
        self.opener = opener or os.startfile
        self.ask_files = ask_files
        self.busy = False
        self.rows = []
        self.out_path = None
        self.exclude = {}
        self.counts = {}

    def build(self, frame, ctx):
        super().build(frame, ctx)
        s = ctx.s
        body = self.page("Daily RIAs", "Turns the day's RIA list from EDMS into a printable tick sheet. "
                                       "Separate from the checklist comparison.")
        self.sub.pack_forget()
        self.sub.master.pack_configure(pady=(s(8), s(10)))     # baslik: ortak sayfadan daha sik
        self._bar.pack_configure(pady=(s(10), s(12)))
        bar = self.action_bar()
        self.make_btn = ui.Button(bar, "Create sheet", self.create, kind="primary", size=11, padx=s(22), pady=s(10))
        self.make_btn.pack(side="right")
        self.folder_btn = ui.Button(bar, "Show in folder", self.open_folder, pady=s(10))
        self.folder_btn.pack(side="right", padx=(0, s(10)))

        # 1 -- RIA listesi
        # Leave out'a yer kalsin diye (6 parca satiri sigsin): alt yazi yok, birakma seridi
        # ve dosya adi "1 RIA list" ile ayni satirda
        self.files = self._label(body, "1", "RIA list")
        self.zone = tk.Canvas(self.files.master, bg=theme.PAPER, highlightthickness=0, bd=0, height=s(36),
                              cursor="hand2")
        self.zone.pack(side="left", fill="x", expand=True)
        self.zone.bind("<Configure>", lambda e: self._draw_zone())
        self.zone.bind("<Button-1>", lambda e: self.browse())

        # 2 -- eleme
        self._label(body, "2", "Leave out", top=s(10))
        c = ui.card(body)
        c.pack(fill="both", expand=True, pady=(s(4), 0))
        self.rules_row = tk.Frame(c, bg=theme.SHEET_HI)
        self.rules_row.pack(fill="x", side="bottom")
        tk.Frame(c, bg=theme.RULE, height=1).pack(fill="x", side="bottom")
        self.scroll = ui.Scroll(c)
        self.scroll.pack(fill="both", expand=True, padx=s(20), pady=(s(6), s(2)))
        self.chips = PartChips(self.scroll.body, ctx.S, self.values, self.is_on, self.toggle, self.set_all,
                               count=self.count)
        self.chips.pack(fill="x")
        self.refresh()

    def _label(self, parent, n, text, top=0):
        s = self.ctx.s
        f = tk.Frame(parent, bg=theme.PAPER)
        f.pack(fill="x", pady=(top, 0))
        tk.Label(f, text=n, bg=theme.INK, fg=theme.SHEET, font=theme.mono(9, "Bold"), width=2).pack(side="left")
        tk.Label(f, text=text, bg=theme.PAPER, fg=theme.INK, font=theme.font(11, "Semibold")).pack(
            side="left", padx=(s(8), 0))
        extra = tk.Frame(f, bg=theme.PAPER)
        extra.pack(side="left", padx=(s(18), s(12)))
        return extra

    # --- filtre (Filter adimiyla ayni kutucuklar) ------------------------------
    def values(self, part):
        seen = self.counts.get(part, {})
        return [v for v, _ in sorted(seen.items(), key=lambda kv: (-kv[1], kv[0]))]

    def count(self, part, value):
        return self.counts.get(part, {}).get(value, 0)

    def is_on(self, part, value):
        return value not in self.exclude.get(part, ())

    def toggle(self, part, value):
        cur = set(self.exclude.get(part, ()))
        cur.symmetric_difference_update({value})
        self.exclude[part] = cur
        self._save()

    def set_all(self, part, on):
        vals = set(self.values(part))
        cur = set(self.exclude.get(part, ())) - vals
        self.exclude[part] = cur if on else cur | vals
        self._save()

    def _save(self):
        settings.save_daily_exclude(self.exclude)
        self.refresh(reload=False)

    # --- islemler -------------------------------------------------------------
    def browse(self):
        if self.busy:
            return
        paths = self.ask_files() if self.ask_files else filedialog.askopenfilenames(
            parent=self.ctx.root, title="Choose the RIA list", filetypes=[("Excel", "*.xlsx *.xlsm")])
        if paths:
            self.add(paths)

    def add(self, paths, wait=False):
        """Files adimindaki gibi arka planda okur; oturuma eklenir."""
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
        if wait:
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

    def create(self):
        if not self.rows:
            return
        try:
            today = dt.date.today()
            self.out_path = dailyrias.write(self.rows, output.unique_path(
                output.day_dir(today) / dailyrias.FILE_NAME.format(day=today)))
        except OSError as e:
            self.out_path = None
            self.sum1.config(text="Could not save the Excel", fg=theme.RED)
            self.sum2.config(text=f"{e.__class__.__name__}: close it in Excel and try again.")
            return
        self.opener(str(self.out_path))
        self.refresh(reload=False)

    def open_folder(self):
        if self.out_path and self.out_path.exists():
            subprocess.Popen(["explorer", "/select,", str(self.out_path)])

    def show(self):
        self.ctx.drop_to = self.add          # bu sekme acikken birakilan dosyalar buraya
        self.refresh()
        self.scroll.top()

    def hide(self):
        self.ctx.drop_to = None

    # --- cizim ----------------------------------------------------------------
    def _draw_zone(self):
        cv = self.zone
        cv.delete("all")
        W, H = cv.winfo_width(), cv.winfo_height()
        if W <= 1:
            return
        cv.create_rectangle(1, 1, W - 2, H - 2, fill=theme.SHEET, outline=theme.RULE_DARK, dash=(6, 4))
        if self.busy:
            cv.create_text(W / 2, H / 2, text="Reading files…", fill=theme.MUTED, font=theme.font(11, "Semibold"))
            return
        cv.create_text(W / 2, H / 2, text="Drop the day's RIA Excel here  ·  or click to browse" if not self.ctx.session.rias
                       else "Drop another to add  ·  or click to browse",
                       fill=theme.INK, font=theme.font(10, "Semibold"))

    def refresh(self, reload=True):
        if not hasattr(self, "chips"):
            return
        s, rias = self.ctx.s, self.ctx.session.rias
        if reload:
            self.exclude = settings.load_daily_exclude()
            numbers = [r[t.header.index(detect.RIA_KEY)] for t in rias for r in t.rows]
            self.counts = riafilter.counts(numbers)
        self._draw_zone()
        self.chips.redraw()
        for w in self.files.winfo_children():
            w.destroy()
        for t in rias:
            row = tk.Frame(self.files, bg=theme.PAPER)
            row.pack(side="left", padx=(0, s(16)))
            tk.Label(row, text="✓", bg=theme.PAPER, fg=theme.GREEN, font=theme.font(10, "Bold")).pack(side="left")
            tk.Label(row, text=ui.fit_text(t.path.name, theme.font(10), s(520)), bg=theme.PAPER, fg=theme.INK,
                     font=theme.font(10)).pack(side="left", padx=(s(6), s(10)))
            tk.Label(row, text=ui.plural(len(t.rows), "RIA"), bg=theme.PAPER, fg=theme.MUTED,
                     font=theme.mono(8)).pack(side="left")
            x = tk.Label(row, text="✕", bg=theme.PAPER, fg=theme.FAINT, font=theme.font(9), cursor="hand2")
            x.pack(side="left", padx=(s(10), 0))
            x.bind("<Button-1>", lambda e, p=t.path: self.remove(p))

        rules = settings.load_rules()
        self.rows, gone, error = [], Counter(), ""
        if rias:
            try:
                self.rows = dailyrias.rows_for(rias, self.exclude, rules)
                gone = dailyrias.removed(rias, self.exclude, rules)
            except dailyrias.DailyRiasError as e:
                error = str(e)
        self._rules_row(rules, gone)
        self.make_btn.set_enabled(bool(self.rows) and not self.busy)
        self.folder_btn.set_enabled(bool(self.out_path))
        if not rias:
            self.sum1.config(text="No RIA list yet", fg=theme.INK)
            self.sum2.config(text="Download the day's RIA list from EDMS and drop it above.")
        elif error:
            self.sum1.config(text="This list can't be used", fg=theme.RED)
            self.sum2.config(text=error)
        elif not self.rows:
            self.sum1.config(text="Every RIA is left out", fg=theme.INK)
            self.sum2.config(text="Tick some values back on below.")
        else:
            by = Counter(x[3] or "(no department)" for x in self.rows)
            left = sum(gone.values())
            self.sum1.config(text=f"{ui.plural(len(self.rows), 'RIA')} on the sheet"
                                  + (f"  ·  {left:,} left out" if left else ""), fg=theme.INK)
            self.sum2.config(text="  ·  ".join(f"{k} {n}" for k, n in by.items()))

    def _rules_row(self, rules, gone):
        s = self.ctx.s
        for w in self.rules_row.winfo_children():
            w.destroy()
        inner = tk.Frame(self.rules_row, bg=theme.SHEET_HI)
        inner.pack(fill="x", padx=s(20), pady=s(6))
        ui.eyebrow(inner, "Also left out", bg=theme.SHEET_HI).pack(side="left", padx=(0, s(14)))
        on = [r for r in rules if r.get("on", True)]
        if not on:
            tk.Label(inner, text="No rules", bg=theme.SHEET_HI, fg=theme.FAINT, font=theme.font(9)).pack(side="left")
        for r in on:
            text = rulemod.describe(r)
            tk.Label(inner, text=f"{text}  ({gone.get(text, 0):,})", bg=theme.SHEET_HI, fg=theme.INK_SOFT,
                     font=theme.font(9)).pack(side="left", padx=(0, s(16)))
        ui.Link(inner, "Edit rules", lambda: self.ctx.go("settings"), bg=theme.SHEET_HI).pack(side="right")
