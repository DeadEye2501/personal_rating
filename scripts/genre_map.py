"""Обслуживание таблицы соответствий жанров.

Источник один — таблицы в `docs/specs/2026-07-27-game-genres.md`. План и
миграция получают словари отсюда, а не набираются руками: соответствий почти
триста, и одна опечатка тихо потеряет жанр.

    pipenv run python scripts/genre_map.py          сверить спеку с планом
    pipenv run python scripts/genre_map.py --dicts  напечатать словари миграции
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/specs/2026-07-27-game-genres.md"
PLAN = ROOT / "docs/plans/2026-07-27-storage.md"

BOOKS = ("STEAM", "STEAM_TAG", "GOG", "GOG_TAG")


def from_spec() -> dict[str, dict[str, list[str]]]:
    """Соответствия из таблиц спеки: источник -> идентификатор -> наши жанры."""
    books: dict[str, dict[str, list[str]]] = {name: {} for name in BOOKS}
    book = ""
    for line in SPEC.read_text(encoding="utf-8").splitlines():
        if line.startswith("### "):
            book = line.removeprefix("### ").strip()
        elif line.startswith("## "):
            # Соответствия кончились: дальше идут таблицы про отвергнутое, и у
            # них те же три колонки.
            book = ""
        cells = [cell.strip() for cell in line.split("|")]
        # Ровно три колонки: у таблицы отвергнутых тегов их четыре.
        if book in books and len(cells) == 5 and cells[1].startswith("`"):
            # Составной идентификатор ведёт в два жанра: «RPG + Tactical».
            books[book][cells[1].strip("`")] = cells[3].split(" + ")
    return books


def from_plan() -> dict[str, dict[str, list[str]]]:
    """Словари из задачи 8 плана — там они уезжают в миграцию."""
    text = PLAN.read_text(encoding="utf-8")
    body = "GAME = [" + text.split("GAME = [")[1].split("\n\n\ndef upgrade")[0]
    scope: dict = {}
    exec(body, scope)  # noqa: S102 — свой же план, не чужой ввод
    return {name: scope[name] for name in BOOKS}


def as_dicts(books: dict[str, dict[str, list[str]]]) -> str:
    blocks = []
    for name in BOOKS:
        lines = [f"{name} = {{"]
        for key, ours in books[name].items():
            names = ", ".join(f'"{one}"' for one in ours)
            lines.append(f'    "{key}": [{names}],')
        blocks.append("\n".join([*lines, "}"]))
    return "\n\n".join(blocks)


def differences(spec: dict, plan: dict) -> list[str]:
    found = []
    for name in BOOKS:
        for key in sorted(spec[name].keys() | plan[name].keys()):
            mine, other = spec[name].get(key), plan[name].get(key)
            if mine != other:
                found.append(f"{name} {key}: спека {mine}, план {other}")
    return found


def main() -> int:
    books = from_spec()
    if "--dicts" in sys.argv:
        print(as_dicts(books))
        return 0

    rows = sum(len(ours) for book in books.values() for ours in book.values())
    found = differences(books, from_plan())
    for line in found:
        print(line)
    print(f"{'разошлись' if found else 'сходятся'}: {rows} строк genre_map")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
