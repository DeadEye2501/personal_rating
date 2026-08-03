"""Что даёт склейка боевым кодом, и чего стоит отсутствие английского названия GOG.

Ключи собираются так, как их производит клиент: у GOG слаг, у old-games второе
название. Английского названия GOG нет — решение пользователя 03.08.2026.
Второй прогон подаёт его, чтобы цена решения была числом, а не мнением.

**Чего этот замер не наблюдает.** Он подаёт в `merged` ровно две строки, то есть
меряет ключи и правила **на парах**. Группировка целой выдачи так не проверяется
вовсе: объединение групп и запрет склейки по составу (`_joinable`) начинают
работать с третьей строки. Отсюда прямое следствие — сторожем боевого кода этот
счёт не является: очередь ключей в `_keys` однажды зависела от хеш-соли
процесса, и здесь это дало бы те же 383/0 и до починки, и после. Группировку
сторожат тесты `tests/backend/test_merging.py`.
"""

import sys

from common import all_pairs
from score_independent import as_editions, labels

from backend.model import Kind, SearchHit, Source
from backend.service.merging import merged

SOURCES = {"S": Source.STEAM, "G": Source.GOG, "O": Source.OLD_GAMES}


def as_hit(row, english: bool) -> SearchHit:
    kind, ident, title, _, raw = row
    aliases, original = (), ""
    if kind == "G":
        aliases = ((raw.get("slug") or "").replace("_", " "),)
        if english:
            original = raw.get("title") or ""
    if kind == "O":
        original = raw.get("alt") or ""
    return SearchHit(
        kind=Kind.GAME, source=SOURCES[kind], source_id=str(ident),
        title=title or "", original_title=original,
        aliases=tuple(one for one in aliases if one),
    )


def glued(a, b, query: str, english: bool) -> bool:
    first, second = as_hit(a, english), as_hit(b, english)
    if not merged([[first]], query)[0] or not merged([[second]], query)[0]:
        return False
    answers = ([[first, second]] if first.source is second.source
               else [[first], [second]])
    return sum(len(one) for one in merged(answers, query)) == 1


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    info, marks = all_pairs(), as_editions(labels())
    total = sum(1 for value in marks.values() if value == "yes")
    won = {}
    for english in (False, True):
        good = bad = 0
        kept = []
        for key, (a, b, query) in info.items():
            if key not in marks or not glued(a, b, query, english):
                continue
            if marks[key] == "yes":
                good += 1
                kept.append((a[2], b[2]))
            else:
                bad += 1
        won[english] = kept
        label = "с английским названием GOG" if english else "как в бою"
        print(f"{label:<28} {good:>3} верных / {bad:>3} ложных "
              f"({good / total * 100:.0f}% из {total})")

    lost = set(map(tuple, won[True])) - set(map(tuple, won[False]))
    print(f"\nцена решения не брать английское название: {len(lost)} пар")
    for one in sorted(lost):
        print("   ", one)


if __name__ == "__main__":
    main()
