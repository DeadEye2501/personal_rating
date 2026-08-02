"""Проба пользователя: ключ — часть названия до двоеточия.

Сравнивается с рекомендованным правилом на той же разметке.
"""

import re
import sys

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

from norm import base, strip_edition
from truth import build

INFO, LABELS, _ = build()

CUT = re.compile(r"\s*[:–—-]\s+")


def head(title):
    """Всё до первого двоеточия или тире-разделителя."""
    return base(CUT.split(title or "", 1)[0])


def extras(row, shape):
    """Дополнительные ключи строки: слаг у GOG, второе название у old-games."""
    kind, _, _, _, raw = row
    if kind == "G" and raw.get("slug"):
        return {shape(raw["slug"].replace("_", " ")),
                shape(raw.get("title") or "")}
    if kind == "O" and raw.get("alt"):
        return {shape(raw["alt"])}
    return set()


def keys_recommended(row):
    keys = {strip_edition(row[2])} | extras(row, strip_edition)
    return {key for key in keys if key}


def keys_colon(row):
    keys = {head(row[2])} | extras(row, head)
    return {key for key in keys if key}


def keys_both(row):
    return keys_recommended(row) | keys_colon(row)


def score(name, keys_of):
    hit = false = missed = 0
    wrong = []
    for (a, b, query) in INFO.values():
        got = bool(keys_of(a) & keys_of(b))
        want = LABELS[tuple(sorted([(a[0], a[1]), (b[0], b[1])]))] == "yes"
        if got and want:
            hit += 1
        elif got:
            false += 1
            wrong.append((a, b, query))
        elif want:
            missed += 1
    print(f"{name:<32} нашло {hit:>3}   ложных {false:>3}   пропустило {missed:>3}")
    return wrong


if __name__ == "__main__":
    score("рекомендованное", keys_recommended)
    wrong = score("до двоеточия", keys_colon)
    score("оба вместе", keys_both)

    print("\nложные склейки правила «до двоеточия» — первые 40:")
    for a, b, query in wrong[:40]:
        print(f"    «{query}»  [{a[0]}] {a[2]}   ||   [{b[0]}] {b[2]}")
