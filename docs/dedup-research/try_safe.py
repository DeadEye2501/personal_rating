"""Свод: только те признаки, что на своём роде пар не ошибаются вовсе."""
import sys

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

from truth import build
from try_strict import close, same_key, score
from try_strict2 import raw_any

INFO, LABELS, _ = build()


def safe(a, b):
    kinds = {a[0], b[0]}
    if kinds == {"G", "S"}:
        return raw_any(a, b)
    if kinds == {"G", "O"}:
        return same_key(a, b) and close(a, b, 1)
    return False


score("безошибочный свод (GS буква в букву, GO ключ+год)", safe)

total = sum(1 for key in INFO if LABELS[key] == "yes")
found = sum(1 for key, (a, b, _) in INFO.items()
            if LABELS[key] == "yes" and safe(a, b))
print(f"\nвсего верных пар в разметке: {total}")
print(f"свод ловит: {found}  ({found / total * 100:.0f}%)")
print(f"остаётся несклеенными: {total - found}")
