"""RIA listesi x checklist karsilastirmasi (GUI'siz).

Anahtar: RIA'da 'Document Number' == checklist'te 'Related RIA' (ayni bicim,
olculdu). Checklist durumundan yalniz REJECTED'e bakilir: o satirlar bastan
hic yokmus gibi atilir; yalniz REJECTED checklist'i olan RIA eksik sayilir
(kullanici 2026-10-14).
"""
from collections import Counter
from dataclasses import dataclass, field

import detect
import riafilter
import rules as rulemod

STATUS_COLUMN = "Status"
DROPPED_STATUS = "REJECTED"


def key(v):
    return str(v).strip().upper() if v not in (None, "") else ""


def combine(tables):
    """Ayni turdeki dosyalari tek tabloda toplar: (header, rows).

    Sutunlar ada gore eslenir; ayni ad bir dosyada iki kez varsa (checklist'te
    iki 'Task Number') sirasiyla ayri sutun kalir. Sonraki dosyada olmayan
    sutun bos, yeni sutun sona eklenir."""
    header, slot = [], {}
    rows = []
    for t in tables:
        seen = Counter()
        idx = []
        for name in t.header:
            k = (name, seen[name])
            seen[name] += 1
            if k not in slot:
                slot[k] = len(header)
                header.append(name)
            idx.append(slot[k])
        for r in t.rows:
            out = [None] * len(header)
            for i, v in zip(idx, r):
                out[i] = v
            rows.append(out)
    n = len(header)
    return header, [r + [None] * (n - len(r)) for r in rows]


@dataclass
class Result:
    ria_header: list
    check_header: list
    matched: list = field(default_factory=list)     # [(ria satiri, checklist satiri)]
    missing: list = field(default_factory=list)     # [ria satiri]
    total: int = 0                                  # dosyalardaki RIA (tekrarsiz)
    duplicates: int = 0                             # birden fazla dosyada gelen ayni RIA
    removed: Counter = field(default_factory=Counter)   # neden -> adet
    orphans: int = 0                                # checklist'te olup tutulan RIA'larda olmayan
    rejected: int = 0                               # atilan REJECTED checklist satiri

    @property
    def kept(self):
        return self.total - sum(self.removed.values())

    @property
    def with_checklist(self):
        return len({key(r[self.ria_header.index(detect.RIA_KEY)]) for r, _ in self.matched})


def ria_rows(tables):
    """Tekrarsiz RIA satirlari: (header, rows, tekrar sayisi). Ayni gun iki kez
    indirilen DataGrid'de ayni RIA iki kez gelir; ilki kalir."""
    header, rows = combine(tables)
    if not header:
        return header, [], 0
    i = header.index(detect.RIA_KEY)
    out, have, dup = [], set(), 0
    for r in rows:
        k = key(r[i])
        if k and k in have:
            dup += 1
            continue
        have.add(k)
        out.append(r)
    return header, out, dup


def run(ria_tables, check_tables, exclude=None, rules=()):
    ria_header, rias, dup = ria_rows(ria_tables)
    check_header, checks = combine(check_tables)
    res = Result(ria_header, check_header, total=len(rias), duplicates=dup)
    if not ria_header:
        return res
    num_i = ria_header.index(detect.RIA_KEY)
    by_ria = {}
    if check_header:
        c_i = check_header.index(detect.CHECKLIST_KEY)
        st_i = check_header.index(STATUS_COLUMN) if STATUS_COLUMN in check_header else None
        for c in checks:
            if st_i is not None and key(c[st_i]) == DROPPED_STATUS:
                res.rejected += 1
                continue
            k = key(c[c_i])
            if k:
                by_ria.setdefault(k, []).append(c)
    kept_keys = set()
    for r in rias:
        why = riafilter.reason(riafilter.parts(r[num_i]), exclude or {}) or rulemod.reason(rules, ria_header, r)
        if why:
            res.removed[why] += 1
            continue
        k = key(r[num_i])
        kept_keys.add(k)
        found = by_ria.get(k)
        if found:
            res.matched += [(r, c) for c in found]
        else:
            res.missing.append(r)
    res.orphans = sum(len(v) for k, v in by_ria.items() if k not in kept_keys)
    return res
