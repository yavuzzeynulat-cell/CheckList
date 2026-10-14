"""RIA parca filtresi (GUI'siz). Handover/src/riafilter.py'nin cekirdegi.

Document Number '-' ile 7 parca: proje-tur-bolum-disiplin-faaliyet-eleman-no.
Ilk 6 parca tiklanarak acilir/kapatilir; kapatilanlar saklanir (izin listesi
degil: hic gorulmemis yeni degerler acik gelir, sessizce kaybolmaz).
"""
from collections import Counter

PARTS = ("Project", "Type", "Section", "Discipline", "Activity", "Element")
NUMBER_COLUMN = "Document Number"
OTHER = "(other)"            # 7 parcali olmayan numaralar


def parts(number):
    p = str(number or "").strip().split("-")
    if len(p) != 7:
        return (OTHER,) * len(PARTS)
    return tuple(x.strip() or OTHER for x in p[0:6])


def excluded(row_parts, exclude):
    """exclude: {parca: kapatilan degerler}."""
    return any(v in exclude.get(name, ()) for name, v in zip(PARTS, row_parts))


def reason(row_parts, exclude):
    """Satiri eleyen ilk kural ('Discipline=C'); elenmiyorsa None."""
    for name, v in zip(PARTS, row_parts):
        if v in exclude.get(name, ()):
            return f"{name}={v}"
    return None


def counts(numbers):
    """{parca: Counter(deger)} -- filtre ekranindaki adet balonlari."""
    rows = [parts(n) for n in numbers]
    return {name: Counter(r[k] for r in rows) for k, name in enumerate(PARTS)}
