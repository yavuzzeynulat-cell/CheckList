"""Settings: varsayilan filtre, eleme kurallari ("Add rule" -- Handover'da
yoktu, kullanici 2026-10-14), cikti klasoru, sifirlama. Her degisiklik hemen
kaydedilir."""
import tkinter as tk
from tkinter import filedialog, ttk

import output
import riafilter
import rules as rulemod
import settings
import theme
import ui
from chips import PartChips
from steps import Step

COMMON_COLUMNS = ["Document Title", "Document Number", "Department Codes", "Action Status", "RIA Status",
                  "Submission Status", "Side"]


class SettingsStep(Step):
    key = "settings"
    title = "Settings"
    bottom = True

    def __init__(self, choose_dir=None):
        self.choose_dir = choose_dir
        self._confirm = False

    def build(self, frame, ctx):
        super().build(frame, ctx)
        s = ctx.s
        body = self.page("Settings", "Changes are saved at once.")
        bar = self.action_bar()
        self.reset_btn = ui.Button(bar, "Reset all settings…", self.reset_all, kind="danger")
        self.reset_btn.pack(side="right")
        self.saved = tk.Label(self._bar, text="", bg=theme.PAPER, fg=theme.GREEN, font=theme.font(9, "Semibold"))
        self.saved.pack(side="right", padx=(0, s(16)))
        body.columnconfigure(0, weight=1, uniform="c")
        body.columnconfigure(1, weight=1, uniform="c")
        body.rowconfigure(1, weight=1)
        self.c_filter = self._card(body, "Default filter", 0, 0)
        self.c_rules = self._card(body, "Exclusion rules", 0, 1, rowspan=2)
        left2 = tk.Frame(body, bg=theme.PAPER)
        left2.grid(row=1, column=0, sticky="nsew", padx=(0, s(8)), pady=(s(16), 0))
        self.c_out = self._card(left2, "Output folder", None, None)
        self._style()
        self._redraw()

    def _card(self, parent, head, row, col, rowspan=1):
        s = self.ctx.s
        c = ui.card(parent)
        if row is None:
            c.pack(fill="x", pady=(0, s(16)))
        else:
            c.grid(row=row, column=col, rowspan=rowspan, sticky="nsew",
                   padx=(0, s(8)) if col == 0 else (s(8), 0))
        ui.eyebrow(c, head).pack(fill="x", padx=s(20), pady=(s(16), s(8)))
        inner = tk.Frame(c, bg=theme.SHEET)
        inner.pack(fill="both", expand=True, padx=s(20), pady=(0, s(16)))
        return inner

    def _style(self):
        st = ttk.Style(self.ctx.root)
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure("Form.TCombobox", fieldbackground=theme.SHEET, background=theme.SHEET, foreground=theme.INK,
                     bordercolor=theme.RULE_DARK, lightcolor=theme.SHEET, darkcolor=theme.SHEET,
                     arrowcolor=theme.INK, padding=4)
        st.map("Form.TCombobox", fieldbackground=[("readonly", theme.SHEET)],
               bordercolor=[("focus", theme.INK)])

    # --- durum (testler de buradan) -----------------------------------------
    def default_off(self):
        return [(k, sorted(v)) for k, v in sorted(settings.load_default_exclude().items()) if v]

    def reset_filter(self):
        settings.reset_exclude()
        self._saved()

    def add_rule(self, column, op_label, text):
        op = next((k for k, v in rulemod.OPS.items() if v == op_label), op_label)
        rule = {"column": str(column).strip(), "op": op, "text": str(text).strip(), "on": True}
        if not rulemod.valid(rule):
            return False
        items = settings.load_rules()
        if any((r["column"], r["op"], r["text"].casefold()) == (rule["column"], op, rule["text"].casefold())
               for r in items):
            return False
        settings.save_rules(items + [rule])
        self._saved()
        return True

    def toggle_rule(self, i):
        items = settings.load_rules()
        items[i]["on"] = not items[i].get("on", True)
        settings.save_rules(items)
        self._saved()

    def delete_rule(self, i):
        items = settings.load_rules()
        del items[i]
        settings.save_rules(items)
        self._saved()

    def set_out(self, path):
        settings.save_out_dir(path)
        self._saved()

    def reset_all(self):
        if not self._confirm:
            self._confirm = True
            self.ctx.root.after(3500, self._cancel_confirm)
            self._redraw()
            return False
        self._confirm = False
        settings.factory_reset()
        self._saved()
        return True

    def _cancel_confirm(self):
        if self._confirm:
            self._confirm = False
            self._redraw()

    def edit_default(self):
        return DefaultFilterDialog(self.ctx.root, self.ctx.S, self.ctx.session, on_save=self._saved)

    def show(self):
        self._redraw()

    def _saved(self):
        self._redraw()
        if hasattr(self, "saved"):
            self.saved.config(text="✓  Saved")
            self.ctx.root.after(1600, lambda: self.saved.config(text=""))

    # --- cizim ----------------------------------------------------------------
    @staticmethod
    def _clear(f):
        for w in f.winfo_children():
            w.destroy()

    def _redraw(self):
        if not hasattr(self, "c_rules"):
            return
        s = self.ctx.s
        # varsayilan filtre
        f = self.c_filter
        self._clear(f)
        off = self.default_off()
        tk.Label(f, text="Unticked the first time and after “Reset”:", bg=theme.SHEET, fg=theme.MUTED,
                 font=theme.font(9), anchor="w").pack(fill="x")
        if not off:
            tk.Label(f, text="Nothing — everything is kept", bg=theme.SHEET, fg=theme.INK, font=theme.font(10),
                     anchor="w").pack(fill="x", pady=(s(6), 0))
        for part, vals in off:
            row = tk.Frame(f, bg=theme.SHEET)
            row.pack(fill="x", pady=(s(6), 0))
            tk.Label(row, text=part, bg=theme.SHEET, fg=theme.INK, font=theme.font(10, "Semibold"), width=10,
                     anchor="nw").pack(side="left", anchor="n")
            tk.Label(row, text=", ".join(vals), bg=theme.SHEET, fg=theme.INK_SOFT, font=theme.mono(9),
                     anchor="w", justify="left", wraplength=s(330)).pack(side="left", fill="x")
        btns = tk.Frame(f, bg=theme.SHEET)
        btns.pack(fill="x", pady=(s(14), 0))
        ui.Button(btns, "Edit default…", self.edit_default).pack(side="left")
        ui.Button(btns, "Reset filter to default", self.reset_filter).pack(side="left", padx=(s(8), 0))

        # kurallar
        f = self.c_rules
        self._clear(f)
        tk.Label(f, text="RIAs matching a ticked rule are not compared.", bg=theme.SHEET, fg=theme.MUTED,
                 font=theme.font(9), anchor="w").pack(fill="x", pady=(0, s(8)))
        items = settings.load_rules()
        if not items:
            tk.Label(f, text="No rules", bg=theme.SHEET, fg=theme.FAINT, font=theme.font(10), anchor="w").pack(fill="x")
        for i, r in enumerate(items):
            self._rule_row(f, i, r)
        tk.Frame(f, bg=theme.SHEET, height=s(12)).pack(fill="x")
        ui.eyebrow(f, "Add a rule").pack(fill="x", pady=(s(4), s(6)))
        form = tk.Frame(f, bg=theme.SHEET)
        form.pack(fill="x")
        cols = list(dict.fromkeys(self.ctx.session.ria_columns() + COMMON_COLUMNS))
        self.col_box = ttk.Combobox(form, values=cols, style="Form.TCombobox", font=theme.font(10), width=18)
        self.col_box.set("Document Title")
        self.col_box.pack(side="left")
        self.op_box = ttk.Combobox(form, values=list(rulemod.OPS.values()), state="readonly",
                                   style="Form.TCombobox", font=theme.font(10), width=11)
        self.op_box.set(rulemod.OPS["starts"])
        self.op_box.pack(side="left", padx=(s(6), 0))
        self.text_box = tk.Entry(form, bg=theme.SHEET, fg=theme.INK, insertbackground=theme.INK, relief="flat",
                                 font=theme.font(10), highlightthickness=1, highlightbackground=theme.RULE_DARK,
                                 highlightcolor=theme.INK)
        self.text_box.pack(side="left", fill="x", expand=True, padx=(s(6), 0), ipady=s(4))
        self.text_box.bind("<Return>", lambda e: self._add_from_form())
        ui.Button(f, "Add rule", self._add_from_form, kind="primary").pack(anchor="e", pady=(s(10), 0))
        self.form_msg = tk.Label(f, text="", bg=theme.SHEET, fg=theme.RED, font=theme.font(9), anchor="w")
        self.form_msg.pack(fill="x")

        # cikti klasoru
        f = self.c_out
        self._clear(f)
        custom = settings.load_out_dir()
        where = output.base_dir()
        tk.Label(f, text=ui.fit_text(str(where), theme.mono(9), s(400)), bg=theme.SHEET, fg=theme.INK,
                 font=theme.mono(9), anchor="w").pack(fill="x")
        tk.Label(f, text=("Chosen folder" if custom else "Default") + "  ·  a dated folder is made inside",
                 bg=theme.SHEET, fg=theme.MUTED, font=theme.font(8), anchor="w").pack(fill="x", pady=(s(2), 0))
        btns = tk.Frame(f, bg=theme.SHEET)
        btns.pack(fill="x", pady=(s(12), 0))
        ui.Button(btns, "Change…", self._pick_out).pack(side="left")
        if custom:
            ui.Button(btns, "Use default", lambda: self.set_out(None)).pack(side="left", padx=(s(8), 0))

        self.reset_btn.set_text("Click again to reset everything" if self._confirm else "Reset all settings…")

    def _rule_row(self, parent, i, r):
        s = self.ctx.s
        on = r.get("on", True)
        row = tk.Frame(parent, bg=theme.SHEET, highlightthickness=1,
                       highlightbackground=theme.INK if on else theme.RULE)
        row.pack(fill="x", pady=(0, s(6)))
        box = tk.Canvas(row, width=s(16), height=s(16), bg=theme.SHEET, highlightthickness=0, cursor="hand2")
        box.pack(side="left", padx=(s(12), s(10)), pady=s(10))
        ui.checkbox(box, 1, 1, s(14), on)
        text = tk.Frame(row, bg=theme.SHEET)
        text.pack(side="left", fill="x", expand=True)
        tk.Label(text, text=r["column"], bg=theme.SHEET, fg=theme.INK if on else theme.FAINT,
                 font=theme.font(10, "Semibold")).pack(side="left")
        tk.Label(text, text=f" {rulemod.OPS[r['op']]} ", bg=theme.SHEET, fg=theme.MUTED,
                 font=theme.font(10)).pack(side="left")
        tk.Label(text, text=f"“{r['text']}”", bg=theme.SHEET, fg=theme.INK if on else theme.FAINT,
                 font=theme.mono(10)).pack(side="left")
        x = tk.Label(row, text="✕", bg=theme.SHEET, fg=theme.FAINT, font=theme.font(10), cursor="hand2")
        x.pack(side="right", padx=s(12))
        x.bind("<Button-1>", lambda e: self.delete_rule(i))
        x.bind("<Enter>", lambda e: x.config(fg=theme.RED))
        x.bind("<Leave>", lambda e: x.config(fg=theme.FAINT))
        for w in (box, row, text) + tuple(text.winfo_children()):
            w.bind("<Button-1>", lambda e: self.toggle_rule(i))
            w.configure(cursor="hand2")

    def _add_from_form(self):
        if self.add_rule(self.col_box.get(), self.op_box.get(), self.text_box.get()):
            return
        self.form_msg.config(text="Write a column and a text — or this rule is already there.")

    def _pick_out(self):
        p = self.choose_dir() if self.choose_dir else filedialog.askdirectory(parent=self.ctx.root,
                                                                              title="Choose the output folder")
        if p:
            self.set_out(p)


class DefaultFilterDialog:
    """Settings > Edit default…: ilk acilista gelen secim, filtre adimiyla ayni
    kutucuklarla. Save'e basinca yazilir; Cancel hicbir sey degistirmez."""

    def __init__(self, parent, S, session, on_save=None):
        self.on_save = on_save
        self.exclude = {k: set(v) for k, v in settings.load_default_exclude().items()}
        counts = session.part_counts()
        known = [settings.load_default_exclude(), settings.load_exclude(), settings.load_seen_values()]
        self._values = {}
        for part in riafilter.PARTS:
            seen = counts.get(part, {})
            extra = sorted({v for ex in known for v in ex.get(part, ())} - set(seen))
            self._values[part] = [v for v, _ in sorted(seen.items(), key=lambda kv: (-kv[1], kv[0]))] + extra

        def s(v):
            return round(v * S)
        self.win = w = tk.Toplevel(parent, bg=theme.PAPER)
        w.title("Default filter")
        w.transient(parent)
        w.protocol("WM_DELETE_WINDOW", self.close)
        tk.Label(w, text="Default filter", bg=theme.PAPER, fg=theme.INK, font=theme.font(14, "Semibold"),
                 anchor="w").pack(fill="x", padx=s(24), pady=(s(18), 0))
        tk.Label(w, text="Ticked values are kept. Used the first time and when you press “Reset filter to default”.",
                 bg=theme.PAPER, fg=theme.MUTED, font=theme.font(9), anchor="w").pack(fill="x", padx=s(24))
        c = ui.card(w)
        c.pack(fill="both", expand=True, padx=s(24), pady=s(14))
        sc = ui.Scroll(c)
        sc.pack(fill="both", expand=True, padx=s(16), pady=s(14))
        self.chips = PartChips(sc.body, S, lambda p: self._values.get(p, []), self.is_on, self.toggle, self.set_all)
        self.chips.pack(fill="x")
        row = tk.Frame(w, bg=theme.PAPER)
        row.pack(fill="x", padx=s(24), pady=(0, s(18)))
        ui.Button(row, "Save", self.save, kind="primary").pack(side="right")
        ui.Button(row, "Cancel", self.close).pack(side="right", padx=(0, s(8)))
        ui.Link(row, "Copy from the Filter step", self.copy_current, bg=theme.PAPER).pack(side="left")
        w.bind("<Escape>", lambda e: self.close())
        ui.set_icon(w)
        W, H = s(820), s(560)
        w.geometry(f"{W}x{H}+{parent.winfo_rootx() + (parent.winfo_width() - W) // 2}"
                   f"+{parent.winfo_rooty() + (parent.winfo_height() - H) // 3}")
        ui.caption(w)
        try:
            w.grab_set()
        except tk.TclError:
            pass

    def is_on(self, part, value):
        return value not in self.exclude.get(part, ())

    def toggle(self, part, value):
        self.exclude.setdefault(part, set()).symmetric_difference_update({value})
        self.chips.redraw()

    def set_all(self, part, on):
        self.exclude[part] = set() if on else set(self._values.get(part, []))
        self.chips.redraw()

    def copy_current(self):
        self.exclude = {k: set(v) for k, v in settings.load_exclude().items()}
        self.chips.redraw()

    def save(self):
        settings.save_default_exclude(self.exclude)
        self.close()
        if self.on_save:
            self.on_save()

    def close(self):
        try:
            self.win.grab_release()
            self.win.destroy()
        except tk.TclError:
            pass
