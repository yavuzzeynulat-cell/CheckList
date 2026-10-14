"""Eleme kurallari (GUI'siz): 'Document Title starts with Reinforcement' gibi.

Handover'da yalniz basliga bakan sabit bir kelime listesi vardi; burada
kullanici Settings'ten istedigi sutuna kural ekler (kullanici 2026-10-14:
"eleme ekle de olsun, Handover'da bu yoktu"). Buyuk/kucuk harf duyarsiz.
"""
OPS = {"starts": "starts with", "contains": "contains", "equals": "is"}
DEFAULT_RULES = [{"column": "Document Title", "op": "starts", "text": "Reinforcement", "on": True}]


def valid(rule):
    return (isinstance(rule, dict) and isinstance(rule.get("column"), str) and rule["column"].strip()
            and rule.get("op") in OPS and isinstance(rule.get("text"), str) and rule["text"].strip())


def describe(rule):
    return f"{rule['column']} {OPS[rule['op']]} {rule['text']}"


def matches(rule, value):
    if value is None:
        return False
    v = str(value).strip().casefold()
    t = rule["text"].strip().casefold()
    if rule["op"] == "starts":
        return v.startswith(t)
    if rule["op"] == "contains":
        return t in v
    return v == t


def reason(rules, header, row):
    """Satiri eleyen ilk acik kural; elenmiyorsa None. Sutun bu dosyada yoksa
    kural bu dosyaya uygulanmaz (hata degil)."""
    for rule in rules:
        if not rule.get("on", True) or not valid(rule):
            continue
        col = rule["column"].strip()
        if col in header and matches(rule, row[header.index(col)]):
            return describe(rule)
    return None
