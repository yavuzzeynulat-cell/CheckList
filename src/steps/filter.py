"""2. adim: hangi RIA'lar karsilastirilsin. Handover'daki parca filtresi
(tikle ac/kapa, secim hatirlanir) + Settings'teki eleme kurallari."""
import tkinter as tk

import compare
import detect
import riafilter
import rules as rulemod
import settings
import theme
import ui
from chips import PartChips
from steps import Step


class FilterStep(Step):
    key = "filter"
    title = "Filter"

    def __init__(self):
        self.exclude = {}
        self.counts = {}

    def build(self, frame, ctx):
        super().build(frame, ctx)
        s = ctx.s
        body = self.page("Choose which RIAs to compare",
                         "Untick what you don't need — parts of the Document Number. Your choice is saved.")
        bar = self.action_bar()
        self.go_btn = ui.Button(bar, "Compare  →", self.compare, kind="primary", size=11, padx=s(22), pady=s(10))
        self.go_btn.pack(side="right")
        c = ui.card(body)
        c.pack(fill="both", expand=True)
        self.scroll = ui.Scroll(c)
        self.scroll.pack(fill="both", expand=True, padx=s(20), pady=(s(16), s(8)))
        self.chips = PartChips(self.scroll.body, ctx.S, self.values, self.is_on, self.toggle, self.set_all,
                               count=self.count)
        self.chips.pack(fill="x")
        self.rules_row = tk.Frame(c, bg=theme.SHEET_HI)
        self.rules_row.pack(fill="x", side="bottom")
        tk.Frame(c, bg=theme.RULE, height=1).pack(fill="x", side="bottom")

    # --- durum (testler de buradan) -----------------------------------------
    def refresh(self):
        self.exclude = settings.load_exclude()
        self.counts = self.ctx.session.part_counts()
        self._redraw()

    def values(self, part):
        seen = self.counts.get(part, {})
        ordered = sorted(seen.items(), key=lambda kv: (-kv[1], kv[0]))
        return [v for v, _ in ordered]

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
        # Gorunmeyen (bu dosyalarda olmayan) kapali degerler korunur.
        vals = set(self.values(part))
        cur = set(self.exclude.get(part, ())) - vals
        self.exclude[part] = cur if on else cur | vals
        self._save()

    def _save(self):
        settings.save_exclude(self.exclude)
        self._redraw()

    def rule_hits(self):
        """[(kural metni, bu dosyalarda eleyecegi satir)] -- acik kurallar."""
        header, rows, _ = compare.ria_rows(self.ctx.session.rias)
        out = []
        for r in settings.load_rules():
            if not r.get("on", True):
                continue
            n = sum(1 for row in rows if rulemod.reason([r], header, row)) if header else 0
            out.append((rulemod.describe(r), n))
        return out

    def kept(self):
        header, rows, _ = compare.ria_rows(self.ctx.session.rias)
        if not header:
            return 0, 0
        i = header.index(detect.RIA_KEY)
        rules = settings.load_rules()
        k = sum(1 for r in rows if not riafilter.excluded(riafilter.parts(r[i]), self.exclude)
                and not rulemod.reason(rules, header, r))
        return k, len(rows)

    def compare(self):
        if not self.ctx.session.ready:
            return
        self.ctx.session.run(self.exclude, settings.load_rules())
        self.ctx.go("result")

    def show(self):
        self.refresh()
        self.scroll.top()

    # --- cizim ----------------------------------------------------------------
    def _redraw(self):
        if not hasattr(self, "chips"):
            return
        s = self.ctx.s
        self.chips.redraw()
        for w in self.rules_row.winfo_children():
            w.destroy()
        inner = tk.Frame(self.rules_row, bg=theme.SHEET_HI)
        inner.pack(fill="x", padx=s(20), pady=s(10))
        ui.eyebrow(inner, "Also left out", bg=theme.SHEET_HI).pack(side="left", padx=(0, s(14)))
        hits = self.rule_hits()
        if not hits:
            tk.Label(inner, text="No rules", bg=theme.SHEET_HI, fg=theme.FAINT, font=theme.font(9)).pack(side="left")
        for text, n in hits:
            tk.Label(inner, text=f"{text}  ({n:,})", bg=theme.SHEET_HI, fg=theme.INK_SOFT,
                     font=theme.font(9)).pack(side="left", padx=(0, s(16)))
        ui.Link(inner, "Edit rules", lambda: self.ctx.go("settings"), bg=theme.SHEET_HI).pack(side="right")
        k, total = self.kept()
        ready = self.ctx.session.ready
        self.go_btn.set_enabled(ready)
        if not ready:
            self.sum1.config(text="No RIA list yet")
            self.sum2.config(text="Drop a RIA list on the Files step first.")
            return
        self.sum1.config(text=f"{k:,} of {ui.plural(total, 'RIA')} will be compared")
        off = sorted(v for vs in self.exclude.values() for v in vs if any(v in self.counts.get(p, {})
                                                                            for p in riafilter.PARTS))
        self.sum2.config(text=ui.fit_text("Left out: " + ", ".join(off) if off else "Nothing is left out by parts",
                                          theme.font(9), s(620)))
