"""Справочник жанров из миграции против записанного эталона."""

import json
from importlib import import_module
from pathlib import Path

import sqlalchemy
from sqlalchemy import text

from tests.alembic_runner import alembic

MIGRATION = "migrations.versions.0002_genres"

# Эталон соответствий: 326 строк, снятых с согласованных наборов жанров. Лежит
# данными, а не выводится из кода, — иначе сверять было бы не с чем.
REFERENCE = Path(__file__).resolve().parents[1] / "fixtures/genre_map.json"

BOOKS = ("TMDB", "STEAM", "STEAM_TAG", "GOG", "GOG_TAG")

FILM_GENRES = {
    "Боевик", "Вестерн", "Военный", "Детектив", "Детский", "Документальный",
    "Драма", "История", "Комедия", "Криминал", "Мелодрама", "Музыка",
    "Мультфильм", "Мыльная опера", "Новости", "Политика", "Приключения",
    "Реалити-шоу", "Семейный", "Телевизионный фильм", "Ток-шоу", "Триллер",
    "Ужасы", "Фантастика", "Фэнтези",
}

GAME_GENRES = {
    "Action", "Quest", "RPG", "JRPG", "Strategy", "Tabletop", "Tactical",
    "Simulator", "Racing", "Sport", "Shooter", "Platformer", "Metroidvania",
    "Puzzle", "Arcade", "Survival", "Horror", "Stealth", "Roguelike",
    "Sandbox", "Fighting", "Multiplayer",
}

COMPOSITE = {
    "10759": {"Боевик", "Приключения"},
    "10765": {"Фантастика", "Фэнтези"},
    "10768": {"Военный", "Политика"},
}


def named(connection, source: str, ext_id: str) -> set[str]:
    """Наши жанры, в которые ведёт чужой идентификатор."""
    rows = connection.execute(
        text(
            "SELECT g.name FROM genre_map m JOIN genre g ON g.id = m.genre_id "
            "WHERE m.source = :source AND m.ext_id = :ext_id"
        ),
        {"source": source, "ext_id": ext_id},
    ).scalars().all()
    return set(rows)


def test_film_set_has_twenty_five_genres(migrated):
    rows = migrated.execute(
        text("SELECT name FROM genre WHERE kind = 'film'")
    ).scalars().all()
    assert set(rows) == FILM_GENRES
    assert len(rows) == 25


def test_game_set_has_twenty_two_genres(migrated):
    rows = migrated.execute(
        text("SELECT name FROM genre WHERE kind = 'game'")
    ).scalars().all()
    assert set(rows) == GAME_GENRES
    assert len(rows) == 22


def test_tmdb_map_has_thirty_rows_over_twenty_seven_ids(migrated):
    rows = migrated.execute(
        text("SELECT ext_id FROM genre_map WHERE source = 'tmdb'")
    ).scalars().all()
    assert len(rows) == 30
    assert len(set(rows)) == 27


def test_composite_genres_are_split_in_two(migrated):
    for ext_id, expected in COMPOSITE.items():
        assert named(migrated, "tmdb", ext_id) == expected, ext_id


def test_shared_identifiers_map_to_a_single_row(migrated):
    # Восемь id встречаются и в киношном, и в сериальном списке TMDB и означают
    # одно и то же — строка у них одна. «Драма» это 18 в обоих.
    assert named(migrated, "tmdb", "18") == {"Драма"}


def test_game_map_covers_both_stores(migrated):
    # Жанр и тег нумеруются порознь: у Steam 9 — это и жанр «Гонки», и тег
    # «Стратегия». Слитый источник молча выдал бы игре чужой жанр.
    counts = dict(
        migrated.execute(
            text("SELECT source, count(*) FROM genre_map GROUP BY source")
        ).all()
    )
    assert counts == {
        "tmdb": 30, "steam": 8, "steam_tag": 177, "gog": 40, "gog_tag": 71
    }


def test_the_same_number_means_different_things_in_the_two_spaces(migrated):
    """Ловушка, ради которой источников четыре, а не два: у Steam 9 — жанр
    «Гонки» и тег «Стратегия» одновременно."""
    assert named(migrated, "steam", "9") == {"Racing"}
    assert named(migrated, "steam_tag", "9") == {"Strategy"}


def test_only_composite_identifiers_lead_to_two_genres(migrated):
    """Один идентификатор ведёт в два жанра только там, где сам значит два.

    Три сборных жанра TMDB, девять составных тегов Steam вроде `Action RPG`,
    слаг `jrpg` у GOG и три его составных тега. Всё остальное однозначно:
    иначе тег «Стратегия» тихо выдал бы игре ещё и Racing."""
    doubled = migrated.execute(
        text(
            "SELECT source, count(*) FROM ("
            "  SELECT source, ext_id FROM genre_map "
            "  GROUP BY source, ext_id HAVING count(*) > 1"
            ") GROUP BY source"
        )
    ).all()
    assert dict(doubled) == {"tmdb": 3, "steam_tag": 9, "gog": 1, "gog_tag": 3}


def counted(connection, where: str) -> int:
    return connection.execute(
        text(f"SELECT count(*) FROM genre_map m {where}")
    ).scalar()


def declared_in_migration() -> dict[str, dict[str, list[str]]]:
    """Пять словарей соответствий, как их объявила миграция."""
    module = import_module(MIGRATION)
    return {book: getattr(module, book) for book in BOOKS}


def differences(reference: dict, declared: dict) -> list[str]:
    found = []
    for book in BOOKS:
        for key in sorted(reference[book].keys() | declared[book].keys()):
            mine, other = reference[book].get(key), declared[book].get(key)
            if mine != other:
                found.append(f"{book} {key}: эталон {mine}, миграция {other}")
    return found


def test_every_mapping_matches_the_reference():
    """Поимённо соответствия сторожит только эта сверка.

    Тестами проверены числа, ловушки и границы наборов — но подмена жанра у
    одного идентификатора чисел не меняет, и таких строк 326.

    Сверяются два объявления, до базы проверка не доходит. Что объявленное в неё
    доехало, сторожит соседний
    `test_the_declared_mappings_all_reached_the_database`."""
    reference = json.loads(REFERENCE.read_text(encoding="utf-8"))

    assert differences(reference, declared_in_migration()) == []


def test_the_declared_mappings_all_reached_the_database(migrated):
    """Объявленное в миграции против того, что легло в базу: сторожится перенос,
    а не сами таблицы.

    `upgrade` кладёт строки в трёх вложенных циклах, и промахнуться там есть чем:
    привязать пространство к чужому словарю или потерять метку у сборного
    идентификатора — замерено, обе поломки этот тест роняет. Сравниваются тройки
    «источник, чужая метка, имя нашего жанра»: с парой «источник и метка» первая
    из двух прошла бы молча.

    Чего он не ловит и ловить не должен: опечатку в объявленном имени жанра —
    `upgrade` разрешает имя через `ids[(kind, name)]` и роняет саму миграцию, — и
    неверно выбранный жанр для чужой метки: обе стороны сравнения приходят из
    одного объявления. Второе сторожит соседний
    `test_every_mapping_matches_the_reference`; глазами остаётся только промах,
    повторённый и в эталоне."""
    module = import_module(MIGRATION)
    declared = {
        (source, ext_id, name)
        for source, mapping in (
            ("tmdb", module.TMDB), ("steam", module.STEAM),
            ("steam_tag", module.STEAM_TAG), ("gog", module.GOG),
            ("gog_tag", module.GOG_TAG),
        )
        for ext_id, names in mapping.items()
        for name in names
    }

    stored = {
        (row.source, row.ext_id, row.name)
        for row in migrated.execute(text(
            "SELECT m.source, m.ext_id, g.name "
            "FROM genre_map m JOIN genre g ON g.id = m.genre_id"
        ))
    }

    assert stored == declared
    # Множеств меньше, чем строк: одна метка ведёт в два жанра у сборных
    # идентификаторов, и кратность строк множество не показывает. Её сторожит
    # соседний тест числом 326.
    assert len(declared) == counted(migrated, "")


def test_every_mapping_leads_to_an_existing_genre(migrated):
    """Соответствие в никуда — тихая потеря жанра: карточка приедет без него, и
    никто не заметит.

    Сравниваются два числа, а не проверяется отсутствие сирот: на пустой
    таблице сирот нет тоже."""
    joined = counted(migrated, "JOIN genre g ON g.id = m.genre_id")
    assert (joined, counted(migrated, "")) == (326, 326)


def test_the_reference_can_be_rolled_back_and_laid_again(tmp_path):
    """Обратный ход этой миграции — не пустая формальность: она вставляет
    строки, и не убрав их за собой, следующий же прямой ход упирается в
    уникальность имени жанра. Полный откат до пустой базы этого не показывает —
    там строки уходят вместе с таблицами."""
    db_path = tmp_path / "library.db"
    alembic(db_path, "upgrade", "head")
    alembic(db_path, "downgrade", "0001")
    alembic(db_path, "upgrade", "head")

    engine = sqlalchemy.create_engine(f"sqlite:///{db_path}")
    with engine.connect() as connection:
        genres = connection.execute(text("SELECT count(*) FROM genre")).scalar()
        mapped = connection.execute(text("SELECT count(*) FROM genre_map")).scalar()
    engine.dispose()
    assert (genres, mapped) == (47, 326)


def test_film_and_game_sets_never_mix(migrated):
    """Кино и игры — два раздельных набора. Соответствие из магазина, ведущее
    в киношный жанр, значит, что при вставке перепутан набор."""
    right = counted(
        migrated,
        "JOIN genre g ON g.id = m.genre_id "
        "WHERE (m.source = 'tmdb') = (g.kind = 'film')",
    )
    assert right == 326
