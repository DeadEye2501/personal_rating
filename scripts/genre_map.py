"""Сверка соответствий жанров: спека против миграции.

Источник истины — таблицы в спеках: игровая половина в
`docs/specs/2026-07-27-game-genres.md`, киношная в
`docs/specs/2026-07-27-data-model.md`. Миграция получает словари оттуда, а не
набирается руками: соответствий больше трёхсот, и одна опечатка тихо потеряет
жанр — карточка приедет без него, и никто не заметит.

    pipenv run python scripts/genre_map.py

Возвращает 1 при расхождении, поэтому годится и для хука, и для теста.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "migrations/versions/0002_genres.py"

# Книга соответствий -> спека, в которой лежит её таблица.
SPECS = {
    "TMDB": ROOT / "docs/specs/2026-07-27-data-model.md",
    "STEAM": ROOT / "docs/specs/2026-07-27-game-genres.md",
    "STEAM_TAG": ROOT / "docs/specs/2026-07-27-game-genres.md",
    "GOG": ROOT / "docs/specs/2026-07-27-game-genres.md",
    "GOG_TAG": ROOT / "docs/specs/2026-07-27-game-genres.md",
}


def from_spec() -> dict[str, dict[str, list[str]]]:
    """Соответствия из таблиц спек: источник -> идентификатор -> наши жанры."""
    books: dict[str, dict[str, list[str]]] = {name: {} for name in SPECS}
    for path in dict.fromkeys(SPECS.values()):
        book = ""
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("### "):
                book = line.removeprefix("### ").strip()
            elif line.startswith("## "):
                # Соответствия кончились: дальше идут таблицы про отвергнутое,
                # и у них те же три колонки.
                book = ""
            cells = [cell.strip() for cell in line.split("|")]
            # Ровно три колонки: у таблицы отвергнутых тегов их четыре.
            if book in books and len(cells) == 5 and cells[1].startswith("`"):
                # Составной идентификатор ведёт в два жанра: «RPG + Tactical».
                books[book][cells[1].strip("`")] = cells[3].split(" + ")
    return books


def from_migration() -> dict[str, dict[str, list[str]]]:
    """Словари из миграции — то, что реально уезжает в базу."""
    text = MIGRATION.read_text(encoding="utf-8")
    body = "TMDB = {" + text.split("\nTMDB = {")[1].split("\ndef upgrade")[0]
    scope: dict = {}
    # Свой же файл, не чужой ввод: разбирать его парсером ради пяти словарей —
    # лишняя работа.
    exec(body, scope)
    return {name: scope[name] for name in SPECS}


def differences(spec: dict, code: dict) -> list[str]:
    found = []
    for name in SPECS:
        for key in sorted(spec[name].keys() | code[name].keys()):
            mine, other = spec[name].get(key), code[name].get(key)
            if mine != other:
                found.append(f"{name} {key}: спека {mine}, миграция {other}")
    return found


def main() -> int:
    books = from_spec()
    rows = sum(len(ours) for book in books.values() for ours in book.values())
    found = differences(books, from_migration())
    for line in found:
        print(line)
    print(f"{'разошлись' if found else 'сходятся'}: {rows} строк genre_map")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
