"""Ещё формы строгого признака: английское название GOG и второе название."""
import sys

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

from try_strict import RULES, close, score, same_key, same_title


def raws(row):
    """Все написания строки как есть: русское, английское, второе."""
    kind, _, title, _, raw = row
    out = {(title or "").strip()}
    if kind == "G":
        out.add((raw.get("title") or "").strip())
    if kind == "O" and raw.get("alt"):
        out.add(raw["alt"].strip())
    return {one for one in out if one}


def raw_any(a, b):
    return bool(raws(a) & raws(b))


EXTRA = {
    "любое написание буква в букву (оба названия GOG, alt)": raw_any,
    "любое написание + год известен обоим и совпал":
        lambda a, b: raw_any(a, b) and close(a, b, 0),
    "приведённое + год ≤1, ИЛИ буква в букву":
        lambda a, b: (same_title(a, b) and close(a, b, 1)) or raw_any(a, b),
    "ключ + год ≤1, ИЛИ буква в букву":
        lambda a, b: (same_key(a, b) and close(a, b, 1)) or raw_any(a, b),
}

for name, rule in EXTRA.items():
    score(name, rule)
