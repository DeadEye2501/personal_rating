"""Подзаголовок режем только там, где короткая часть содержит число.

«Master of Orion 2» + «…2: Battle at Antares» — одна игра: число уже назвало
конкретную. «Fallout» + «Fallout: New Vegas» — разные: голое имя серии не
называет ничего.
"""
import sys

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

from common import DATA, rows
from truth import build
from try_colon import keys_recommended
from try_prefix import pairs_of, prefix_of

INFO, LABELS, _ = build()


def joins(a, b, per, need_digit, guarded):
    keys = keys_recommended(a) | keys_recommended(b)
    if keys_recommended(a) & keys_recommended(b):
        return True
    for short in keys:
        for long_ in keys:
            if not prefix_of(short, long_):
                continue
            if need_digit and not any(c.isdigit() for c in short):
                continue
            if guarded and any(short in own and long_ in own
                               for own in per.values()):
                continue
            return True
    return False


def score(name, need_digit, guarded):
    hit = false = missed = 0
    wrong = []
    context = {}
    for query in DATA:
        context.update(pairs_of(query))
    for key, (a, b, per) in context.items():
        if key not in LABELS:
            continue
        got = joins(a, b, per, need_digit, guarded)
        want = LABELS[key] == "yes"
        if got and want:
            hit += 1
        elif got:
            false += 1
            wrong.append((a, b))
        elif want:
            missed += 1
    print(f"{name:<46} нашло {hit:>3}  ложных {false:>3}  пропустило {missed:>3}")
    return wrong


if __name__ == "__main__":
    score("только совпадение ключей (рекомендованное)", False, False) if False else None
    score("префикс с числом, без сторожа", True, False)
    wrong = score("префикс с числом + сторож источника", True, True)
    print("\nчто склеилось зря:")
    for a, b in wrong[:20]:
        print(f"    [{a[0]}] {a[2]}   ||   [{b[0]}] {b[2]}")
