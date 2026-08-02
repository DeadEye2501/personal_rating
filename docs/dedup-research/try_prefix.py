"""Подзаголовок отбрасывается, но только если источник сам не возражает.

Мысль пользователя: «Arcanum» и «Arcanum: Of Steamworks» — одна игра. Но
«Fallout» и «Fallout: New Vegas» — разные. Отличает их то, что во втором случае
один источник отдаёт обе строки: этим он и говорит, что игры разные.
"""

import sys

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

from common import DATA, rows
from truth import build
from try_colon import keys_recommended

INFO, LABELS, _ = build()


def prefix_of(short, long_):
    """Строгий префикс по границе слова: «master of orion 2» в «…2 battle at»."""
    return bool(short) and long_ != short and long_.startswith(short + " ")


def own_keys(query):
    """Ключи каждого источника этой выдачи — по отдельности."""
    per = {}
    for row in rows(query):
        per.setdefault(row[0], set()).update(keys_recommended(row))
    return per


def pairs_of(query):
    per = own_keys(query)
    out = {}
    for a in rows(query):
        for b in rows(query):
            if a[0] == b[0] or (a[0], a[1]) >= (b[0], b[1]):
                continue
            out[tuple(sorted([(a[0], a[1]), (b[0], b[1])]))] = (a, b, per)
    return out


def joins(a, b, per, guarded):
    if keys_recommended(a) & keys_recommended(b):
        return True
    for short in keys_recommended(a) | keys_recommended(b):
        for long_ in keys_recommended(a) | keys_recommended(b):
            if not prefix_of(short, long_):
                continue
            if guarded and any(short in keys and long_ in keys
                               for keys in per.values()):
                continue
            return True
    return False


def score(name, guarded):
    hit = false = missed = 0
    wrong = []
    context = {}
    for query in DATA:
        context.update(pairs_of(query))
    for key, (a, b, per) in context.items():
        if key not in LABELS:
            continue
        got = joins(a, b, per, guarded)
        want = LABELS[key] == "yes"
        if got and want:
            hit += 1
        elif got:
            false += 1
            wrong.append((a, b))
        elif want:
            missed += 1
    print(f"{name:<44} нашло {hit:>3}  ложных {false:>3}  пропустило {missed:>3}")
    return wrong


if __name__ == "__main__":
    score("подзаголовок режем всегда", False)
    wrong = score("режем, если источник не возражает", True)
    print("\nчто всё ещё склеивается зря:")
    for a, b in wrong[:25]:
        print(f"    [{a[0]}] {a[2]}   ||   [{b[0]}] {b[2]}")
