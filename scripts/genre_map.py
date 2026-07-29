"""Сверка соответствий жанров: спека против миграции.

Источник истины — таблицы в спеках: игровая половина в
`docs/specs/2026-07-27-game-genres.md`, киношная в
`docs/specs/2026-07-27-data-model.md`. Миграция получает словари оттуда, а не
набирается руками: соответствий больше трёхсот, и одна опечатка тихо потеряет
жанр — карточка приедет без него, и никто не заметит.

    pipenv run python scripts/genre_map.py

Возвращает 1 при расхождении, поэтому годится и для хука, и для теста.
"""

import re
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


def rejected_from_spec() -> set[str]:
    """Слаги GOG, которые спека объявляет известными и отвергнутыми.

    Живут они в отдельном разделе, а не в таблицах соответствий, и в коде им
    отвечает `_REJECTED`: без сверки константа разъедется со спекой молча, а
    следствие тихое — отвергнутое поедет в лог наравне с незнакомым."""
    inside = False
    found: set[str] = set()
    for line in SPECS["GOG"].read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            inside = line.startswith("## Что не переводится")
            continue
        # Пять тегов Steam отвергнуты в том же разделе, но у их таблицы четыре
        # колонки против трёх — по числу ячеек они и отличаются.
        cells = line.split("|")
        if inside and len(cells) == 5:
            found.update(re.findall(r"`([^`]+)`", cells[1]))
    return found


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

    # Импорт здесь, а не наверху: до вставки пути пакет `backend` не виден,
    # а вставка пути — код, после которого импорты уже не ставят.
    sys.path.insert(0, str(ROOT))
    from backend.model import GenreSource
    from backend.storage.repository.genres import REJECTED_SLUGS

    spec_rejected = rejected_from_spec()
    code_rejected = set(REJECTED_SLUGS[GenreSource.GOG])
    for slug in sorted(spec_rejected ^ code_rejected):
        where = "спеке" if slug in spec_rejected else "коде"
        found.append(f"отвергнутый слаг {slug}: есть только в {where}")

    for line in found:
        print(line)
    print(
        f"{'разошлись' if found else 'сходятся'}: {rows} строк genre_map, "
        f"{len(spec_rejected)} отвергнутых слагов"
    )
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
