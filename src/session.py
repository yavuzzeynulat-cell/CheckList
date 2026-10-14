"""Oturum durumu (GUI'siz): birakilan dosyalar, son karsilastirma."""
from dataclasses import dataclass, field

import compare
import detect
import output
import riafilter
import settings


@dataclass
class Session:
    tables: dict = field(default_factory=dict)      # norm(yol) -> detect.Table (birakilma sirasi)
    result: object = None
    out_path: object = None

    def add(self, paths, read=detect.read):
        """Yeni dosyalari okur; zaten listede olanlar atlanir. Yeni Table'lar doner."""
        new = []
        for p in detect.expand_drop(paths):
            k = detect.norm(p)
            if k in self.tables:
                continue
            t = read(p)
            self.tables[k] = t
            new.append(t)
        if new:
            self.result = None
        return new

    def remove(self, path):
        if self.tables.pop(detect.norm(path), None) is not None:
            self.result = None

    def clear(self):
        self.tables.clear()
        self.result = None

    def of(self, kind):
        return [t for t in self.tables.values() if t.kind == kind]

    @property
    def rias(self):
        return self.of(detect.RIA)

    @property
    def checklists(self):
        return self.of(detect.CHECKLIST)

    @property
    def others(self):
        return self.of(detect.OTHER)

    @property
    def ready(self):
        return bool(self.rias)

    def numbers(self):
        """RIA dosyalarindaki Document Number'lar (filtre ekrani icin)."""
        out = []
        for t in self.rias:
            i = t.header.index(detect.RIA_KEY)
            out += [r[i] for r in t.rows]
        return out

    def part_counts(self):
        c = riafilter.counts(self.numbers())
        if any(c[p] for p in riafilter.PARTS):
            settings.save_seen_values({k: list(v) for k, v in c.items()})
        return c

    def ria_columns(self):
        header, _ = compare.combine(self.rias)
        return header

    def run(self, exclude=None, rules=None):
        if exclude is None:
            exclude = settings.load_exclude()
        if rules is None:
            rules = settings.load_rules()
        self.result = compare.run(self.rias, self.checklists, exclude, rules)
        self.out_path = None
        return self.result

    def save(self, folder=None):
        if self.result is None:
            self.run()
        folder = folder or output.day_dir()
        self.out_path = output.write(self.result, output.unique_path(folder / output.FILE_NAME))
        return self.out_path
