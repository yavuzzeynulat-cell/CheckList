"""Kullanici ayarlari (%APPDATA%\\CheckList\\settings.json).

Handover'daki mantik: parca filtresinde kapatilan degerler saklanir (yeni
gelen degerler acik), ilk acilista 'default' secim gelir; eleme kurallari ve
cikti klasoru de burada.
"""
import json
import os
from pathlib import Path

import rules as rulemod

PATH = Path(os.environ.get("APPDATA", str(Path.home()))) / "CheckList" / "settings.json"

# Ilk acilista kapali gelenler (Handover ile ayni gunluk filtre: Activity'de
# yalniz IN2, PLE, PR2, GR2, SLP acik -- kullanici 2026-10-09).
DEFAULT_EXCLUDE = {"Activity": {"GEM", "EXC", "IST", "PR1", "IN1", "CLG", "REF", "REX", "GR1", "WP3",
                                "WTS", "SNL", "ZRM", "OTH", "SBB"}}


def _read():
    try:
        data = json.loads(PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write(data):
    try:
        PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(tmp, PATH)
    except OSError:
        pass        # kaydedemezsek ayar yalniz bu oturumda gecerli


def _as_exclude(data):
    if not isinstance(data, dict):
        return {}
    return {k: {str(x) for x in v} for k, v in data.items() if isinstance(v, list) and v}


def _set(name, value):
    data = _read()
    data[name] = value
    _write(data)


# --- parca filtresi ---------------------------------------------------------
def load_default_exclude():
    raw = _read()
    if isinstance(raw.get("default_exclude"), dict):
        return _as_exclude(raw["default_exclude"])
    return {k: set(v) for k, v in DEFAULT_EXCLUDE.items()}


def save_default_exclude(exclude):
    _set("default_exclude", {k: sorted(v) for k, v in exclude.items() if v})


def load_exclude():
    raw = _read()
    if "exclude" not in raw:
        return load_default_exclude()
    return _as_exclude(raw["exclude"])


def save_exclude(exclude):
    _set("exclude", {k: sorted(v) for k, v in exclude.items() if v})


def reset_exclude():
    save_exclude(load_default_exclude())


def load_seen_values():
    data = _read().get("seen_values")
    if not isinstance(data, dict):
        return {}
    return {k: [str(x) for x in v] for k, v in data.items() if isinstance(v, list)}


def save_seen_values(counts):
    """counts: {parca: degerler}; eskilere eklenir (silinmez)."""
    old = load_seen_values()
    new = {k: sorted(set(old.get(k, [])) | {str(v) for v in vals}) for k, vals in counts.items()}
    for k, v in old.items():
        new.setdefault(k, v)
    if new != old:
        _set("seen_values", new)


# --- eleme kurallari --------------------------------------------------------
def load_rules():
    raw = _read().get("rules")
    if not isinstance(raw, list):
        return [dict(r) for r in rulemod.DEFAULT_RULES]
    return [{"column": r["column"].strip(), "op": r["op"], "text": r["text"].strip(),
             "on": r.get("on", True) is not False} for r in raw if rulemod.valid(r)]


def save_rules(items):
    _set("rules", [dict(r) for r in items if rulemod.valid(r)])


# --- cikti klasoru ----------------------------------------------------------
def load_out_dir():
    p = _read().get("out_dir")
    return Path(p) if isinstance(p, str) and p and Path(p).is_dir() else None


def save_out_dir(path):
    _set("out_dir", str(path) if path else "")


def factory_reset():
    data = _read()
    for k in ("default_exclude", "exclude", "rules", "out_dir"):
        data.pop(k, None)
    _write(data)
