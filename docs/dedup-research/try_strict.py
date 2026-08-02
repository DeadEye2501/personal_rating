"""Есть ли признак, который не ошибается вовсе? Ищем правила с нулём ложных.

Считается отдельно по родам пар: у Steam в выдаче есть только название, поэтому
год и компании применимы лишь к парам GOG↔old-games.
"""

import re
import sys

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

from norm import base
from truth import build
from try_colon import keys_recommended

INFO, LABELS, _ = build()

YEAR = re.compile(r"(19|20)\d{2}")


def year_of(row):
    """Год из выдачи. У Steam его в выдаче нет вовсе — только в карточке."""
    kind, _, _, _, raw = row
    if kind == "G":
        head = (raw.get("year") or "")[:4]
        return int(head) if head.isdigit() else None
    if kind == "O":
        found = YEAR.search(raw.get("year") or "")
        return int(found.group()) if found else None
    return None


def companies(row):
    kind, _, _, _, raw = row
    if kind == "G":
        names = (raw.get("developers") or []) + (raw.get("publishers") or [])
    elif kind == "O":
        names = [raw.get("publisher")] if raw.get("publisher") else []
    else:
        names = []
    return {base(name) for name in names if name}


def same_raw(a, b):
    """Название совпало буква в букву, без всякого приведения."""
    return (a[2] or "").strip() == (b[2] or "").strip() and (a[2] or "").strip()


def same_title(a, b):
    return base(a[2]) == base(b[2]) and base(a[2]) != ""


def same_key(a, b):
    return bool(keys_recommended(a) & keys_recommended(b))


def close(a, b, gap):
    one, two = year_of(a), year_of(b)
    return one is not None and two is not None and abs(one - two) <= gap


RULES = {
    "название буква в букву, без приведения":
        same_raw,
    "название совпало после приведения":
        same_title,
    "приведённое + год известен обоим и совпал":
        lambda a, b: same_title(a, b) and close(a, b, 0),
    "приведённое + год расходится не больше чем на 1":
        lambda a, b: same_title(a, b) and close(a, b, 1),
    "приведённое + год не больше чем на 3":
        lambda a, b: same_title(a, b) and close(a, b, 3),
    "приведённое + общая компания":
        lambda a, b: same_title(a, b) and bool(companies(a) & companies(b)),
    "приведённое + год совпал + общая компания":
        lambda a, b: same_title(a, b) and close(a, b, 0)
        and bool(companies(a) & companies(b)),
    "ключ рекомендованного (со снятием изданий)":
        same_key,
    "ключ + год известен обоим и совпал":
        lambda a, b: same_key(a, b) and close(a, b, 0),
    "ключ + год не больше чем на 1":
        lambda a, b: same_key(a, b) and close(a, b, 1),
    "ключ + общая компания":
        lambda a, b: same_key(a, b) and bool(companies(a) & companies(b)),
}


def score(name, rule):
    counts = {}
    for key, (a, b, _) in INFO.items():
        if not rule(a, b):
            continue
        slot = counts.setdefault("".join(sorted([a[0], b[0]])), [0, 0])
        slot[0 if LABELS[key] == "yes" else 1] += 1
    good = sum(pair[0] for pair in counts.values())
    bad = sum(pair[1] for pair in counts.values())
    parts = "  ".join(f"{kind} {pair[0]}/{pair[1]}"
                      for kind, pair in sorted(counts.items()))
    mark = "   ← БЕЗ ОШИБОК" if bad == 0 and good else ""
    print(f"{name:<46} {good:>3} верных / {bad:>3} ложных   [{parts}]{mark}")


if __name__ == "__main__":
    print("в скобках — по родам пар «верных/ложных»: "
          "GO = gog↔old-games, GS = gog↔steam, OS = old-games↔steam\n")
    for name, rule in RULES.items():
        score(name, rule)
