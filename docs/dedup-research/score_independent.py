"""Правила дедупликации против независимой разметки от 03.08.2026.

Прежняя разметка (`truth.py`) строилась предикатом `base`/`strip_edition` с
ручными списками исключений — тем же приведением, которым правила и
проверяются, поэтому «ноль ложных» у неё был частично тавтологичен. Эта считает
по кластерам из `clusters/`: их размечали двенадцать судей, каждый видел строки
запроса и правило из `clusters/rubric.md`, и ни правил-кандидатов, ни старых
меток им не показывали.

Запуск из этой папки: python score_independent.py
"""

import itertools
import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

from common import all_pairs
from norm import strip_edition

INFO = all_pairs()
CLUSTERS = Path(__file__).parent / "clusters"

# Набор из нескольких игр — не издание. По решению пользователя 03.08.2026 он
# убирается из выдачи вовсе, если слова сборника нет в самой строке поиска.
SETS = ("bundle", "collection", "trilogy", "anthology", "антология",
        "коллекция", "compilation")

# Слова издания, которые снятие хвоста не убирает: они стоят не последними либо
# написаны иначе.
EDITIONS = ("redux", "black edition", " vr")


def labels() -> dict:
    """Метка пары: вместе в одной группе судьи — одна игра."""
    together, seen = set(), set()
    for path in sorted(CLUSTERS.glob("clusters_*.json")):
        for entry in json.loads(path.read_text(encoding="utf-8")):
            seen.add(entry["query"])
            for cluster in entry["clusters"]:
                ids = cluster["ids"] if isinstance(cluster, dict) else cluster
                together.update(frozenset(pair)
                                for pair in itertools.combinations(ids, 2))
    marks = {}
    for key, (a, b, query) in INFO.items():
        if query in seen:
            pair = frozenset((f"{a[0]}{a[1]}", f"{b[0]}{b[1]}"))
            marks[key] = "yes" if pair in together else "no"
    return marks


def year_of(row):
    """Год из выдачи. У Steam его там нет вовсе — только в карточке."""
    kind, _, _, _, raw = row
    head = (raw.get("year") or "")[:4]
    if kind == "O":
        head = "".join(char for char in head if char.isdigit())
    return int(head) if len(head) == 4 and head.isdigit() else None


def keys(row, inside: bool) -> set:
    """Ключи строки. Внутри одного магазина — только показываемое название:
    второе название old-games там склеивает разные игры одной серии, замерено
    03.08.2026 (`Worms` с `Worms 2`, `Space Quest I` со `Space Quest II`)."""
    kind, _, shown, _, raw = row
    out = {strip_edition(shown)}
    if not inside and kind == "G":
        out.add(strip_edition((raw.get("slug") or "").replace("_", " ")))
        out.add(strip_edition(raw.get("title") or ""))
    if not inside and kind == "O" and raw.get("alt"):
        out.add(strip_edition(raw["alt"]))
    return {one for one in out if one}


def a_set(row) -> bool:
    return any(word in (row[2] or "").lower() for word in SETS)


def merged(a, b) -> bool:
    """Правило целиком: сборник не склеивается ни с чем, остальное — по любому
    совпавшему ключу."""
    if a_set(a) or a_set(b):
        return False
    return bool(keys(a, a[0] == b[0]) & keys(b, a[0] == b[0]))


def narrow(a, b) -> bool:
    """Прежний свод в самом узком его виде: буква в букву у GOG со Steam и
    приведённый ключ с годом ±1 у GOG со old-games — по одному показываемому
    названию, без слага и второго написания. В богатом наборе ключей тот же
    свод давал 179 верных при нуле ложных."""
    kinds = {a[0], b[0]}
    if kinds == {"G", "S"}:
        return (a[2] or "").strip() == (b[2] or "").strip() != ""
    if kinds == {"G", "O"}:
        one, two = year_of(a), year_of(b)
        return (strip_edition(a[2]) == strip_edition(b[2]) != ""
                and one is not None and two is not None and abs(one - two) <= 1)
    return False


def as_editions(marks: dict) -> dict:
    """Разные издания одной игры — одна игра, решение пользователя 03.08.2026.

    Судьи расходились именно здесь: одни считали ремастер изданием, другие
    переделкой. Решение снимает разночтение, и здесь оно применяется к меткам."""
    wider = dict(marks)
    for key, (a, b, _) in INFO.items():
        if marks.get(key) != "no" or a_set(a) or a_set(b):
            continue
        words = f"{a[2]} {b[2]}".lower()
        same = strip_edition(a[2]) == strip_edition(b[2]) != ""
        if same or any(word in words for word in EDITIONS):
            wider[key] = "yes"
    return wider


def score(name: str, marks: dict, rule) -> None:
    total = sum(1 for value in marks.values() if value == "yes")
    good = bad = 0
    for key, (a, b, _) in INFO.items():
        if key not in marks or not rule(a, b):
            continue
        if marks[key] == "yes":
            good += 1
        else:
            bad += 1
    print(f"{name:<38} {good:>3} верных / {bad:>3} ложных "
          f"({good / total * 100:.0f}% из {total})")


if __name__ == "__main__":
    marks = labels()
    print(f"пар под меткой: {len(marks)}\n")
    for name, table in (("как разметили судьи", marks),
                        ("издания склеены решением", as_editions(marks))):
        print(name)
        score("  свод по показываемому названию", table, narrow)
        score("  принятое правило", table, merged)
        print()

    wider = as_editions(marks)
    missed = [(query, a, b) for key, (a, b, query) in INFO.items()
              if wider.get(key) == "yes" and not merged(a, b)]
    print(f"не склеилось, хотя одна игра: {len(missed)}")
    for query, a, b in missed[:15]:
        print(f"   «{query}» [{a[0]}] {a[2]}  ||  [{b[0]}] {b[2]}")
