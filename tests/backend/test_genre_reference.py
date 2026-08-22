"""Справочник жанров из миграции против записанного эталона.

Как правила срабатывают — `test_genre_rules.py`; здесь только то, что объявлено
и что из объявленного доехало до базы."""

import json
from importlib import import_module
from pathlib import Path

import sqlalchemy
from sqlalchemy import text

from tests.alembic_runner import alembic

# Справочник разлит двумя миграциями: кино с играми ревизией 0002, книги с
# музыкой — 0003. Читаются обе: сверка идёт со всей базой, и одна забытая
# ревизия дала бы расхождение там, где всё верно.
MIGRATIONS = ("migrations.versions.0002_genres", "migrations.versions.0003_tracks")

# Эталон правил: снимок, снятый с объявления один раз и с тех пор замороженный.
# Он не проверяет сегодняшний перенос из спеки — это работа глаз и ревью; его
# дело — уронить сборку, когда правило поправят мимоходом, а таких правил 363, и
# счётом ни одна подмена метки не видна.
#
# **Пересобирать его вслепую нельзя.** Он единственный сторож этих 363 строк
# поимённо, и пересборка «чтобы позеленело» обнуляет его молча: сперва читают,
# что именно разошлось, и только потом снимают снимок заново.
REFERENCE = Path(__file__).resolve().parents[1] / "fixtures/genre_rules.json"

FILM_GENRES = {
    "Боевик", "Вестерн", "Военный", "Детектив", "Детский", "Документальный",
    "Драма", "История", "Комедия", "Криминал", "Мелодрама", "Музыка",
    "Мультфильм", "Мыльная опера", "Новости", "Политика", "Приключения",
    "Реалити-шоу", "Семейный", "Телевизионный фильм", "Ток-шоу", "Триллер",
    "Ужасы", "Фантастика", "Фэнтези",
}

GAME_GENRES = {
    "Action", "Shooter", "Action-RPG", "RPG", "Strategy", "Tactical",
    "Fighting", "Platformer", "Quest", "Puzzle", "Survival", "Tabletop",
    "Sport", "Racing", "Simulator", "Horror", "Multiplayer", "Roguelike",
    "Arcade",
}

COMPOSITE = {
    "10759": {"Боевик", "Приключения"},
    "10765": {"Фантастика", "Фэнтези"},
    "10768": {"Военный", "Политика"},
}

RULES = 432
MARKS = 454


def named(connection, source: str, ext_id: str) -> set[str]:
    """Наши жанры, к которым ведёт чужая метка. Запреты не в счёт: метка,
    стоящая в правиле запретом, к его жанру не ведёт, а мешает."""
    rows = connection.execute(
        text(
            "SELECT g.name FROM genre_rule r "
            "JOIN genre g ON g.id = r.genre_id "
            "JOIN genre_rule_mark m ON m.rule_id = r.id "
            "WHERE r.source = :source AND m.ext_id = :ext_id "
            "AND m.forbidden = 0"
        ),
        {"source": source, "ext_id": ext_id},
    ).scalars().all()
    return set(rows)


def counted(connection, table: str, where: str = "") -> int:
    return connection.execute(
        text(f"SELECT count(*) FROM {table} {where}")
    ).scalar()


def test_film_set_has_twenty_five_genres(migrated):
    rows = migrated.execute(
        text("SELECT name FROM genre WHERE kind = 'film'")
    ).scalars().all()
    assert set(rows) == FILM_GENRES
    assert len(rows) == 25


def test_game_set_has_nineteen_genres(migrated):
    """Набор пересмотрен пользователем 02.08.2026: прежние двадцать два
    отменены, дробления на поджанры не будет."""
    rows = migrated.execute(
        text("SELECT name FROM genre WHERE kind = 'game'")
    ).scalars().all()
    assert set(rows) == GAME_GENRES
    assert len(rows) == 19


BOOK_GENRES = {
    "Фантастика", "Фэнтези", "Ужасы", "Детектив", "Приключения", "Романтика",
    "Классика", "Исторический", "Юмор", "Драма", "Детское", "Рассказы",
    "Сборник", "Проза", "Биография", "История", "Философия", "Психология",
    "Саморазвитие", "Бизнес", "Наука", "Программирование",
}

MUSIC_GENRES = {
    "African Music", "Alternative", "Asian Music", "Blues", "Brazilian Music",
    "Classical", "Dance", "Electro", "Films/Games", "Folk", "Indian Music",
    "Jazz", "Kids", "Latin Music", "Metal", "Pop", "R&B", "Rap/Hip Hop",
    "Reggae", "Rock", "Soul & Funk",
}


def test_book_set_has_twenty_two_genres(migrated):
    """Имена русские, как у кино: набор выведен из верхних двух уровней BISAC,
    которые отдаёт Google Books, и утверждён пользователем 22.08.2026."""
    rows = migrated.execute(
        text("SELECT name FROM genre WHERE kind = 'book'")
    ).scalars().all()
    assert set(rows) == BOOK_GENRES
    assert len(rows) == 22


def test_music_set_has_twenty_one_genres(migrated):
    """Имена английские, как у игр, и взяты у Deezer как есть — верхний уровень
    его дерева без `All`, который жанром не является."""
    rows = migrated.execute(
        text("SELECT name FROM genre WHERE kind = 'music'")
    ).scalars().all()
    assert set(rows) == MUSIC_GENRES
    assert len(rows) == 21


def test_book_and_music_rules_lead_to_their_own_sets(migrated):
    """Источник обязан вести в свой набор: перепутай `kind` в разливке — и
    книжное правило привело бы в музыкальный жанр. Числа этого не видят, а
    эталон сверяет имена, не проверяя, куда они привязаны."""
    for source, kind in (("google_books", "book"), ("deezer", "music")):
        wrong = migrated.execute(
            text("SELECT count(*) FROM genre_rule r "
                 "JOIN genre g ON g.id = r.genre_id "
                 "WHERE r.source = :source AND g.kind != :kind"),
            {"source": source, "kind": kind},
        ).scalar()
        assert wrong == 0, source


def test_composite_genres_are_split_in_two(migrated):
    """У TMDB сборный жанр — это два наших, и записан он двумя правилами с
    одной меткой: правила с двумя жанрами не бывает."""
    for ext_id, expected in COMPOSITE.items():
        assert named(migrated, "tmdb", ext_id) == expected, ext_id


def test_shared_identifiers_map_to_a_single_rule(migrated):
    # Восемь id встречаются и в киношном, и в сериальном списке TMDB и означают
    # одно и то же — правило у них одно. «Драма» это 18 в обоих.
    assert named(migrated, "tmdb", "18") == {"Драма"}


def test_every_source_has_the_rules_it_should(migrated):
    """Числа правил по источникам. Колонка old-games.ru лежит в базе раньше,
    чем появится его клиент: справочник — один артефакт, и собирать его дважды
    дороже, чем подержать тринадцать строк без потребителя один слайс."""
    counts = dict(
        migrated.execute(
            text("SELECT source, count(*) FROM genre_rule GROUP BY source")
        ).all()
    )
    assert counts == {"tmdb": 30, "steam": 219, "gog": 101, "old_games": 13,
                      "google_books": 48, "deezer": 21}


def test_every_rule_requires_at_least_one_mark(migrated):
    """Правило из одних запретов сработало бы на любой игре без них — то есть
    почти на всех."""
    empty = migrated.execute(
        text(
            "SELECT count(*) FROM genre_rule r WHERE NOT EXISTS ("
            "  SELECT 1 FROM genre_rule_mark m "
            "  WHERE m.rule_id = r.id AND m.forbidden = 0)"
        )
    ).scalar()
    assert (empty, counted(migrated, "genre_rule")) == (0, RULES)


def declared_in_migration() -> dict[str, list[list]]:
    """Правила, как их объявили миграции, — в форме эталона."""
    return {
        source: [[rule.genre, rule.required(), rule.forbidden(), rule.alone]
                 for rule in rules]
        for name in MIGRATIONS
        for source, rules, _kind in import_module(name).BOOKS
    }


def test_every_rule_matches_the_reference():
    """Поимённо правила сторожит только эта сверка.

    Тестами проверены числа, границы наборов и сами срабатывания — но подмена
    метки у одного правила чисел не меняет, а правил 363.

    Сверяются два объявления, до базы проверка не доходит. Что объявленное в
    неё доехало, сторожит соседний
    `test_the_declared_rules_all_reached_the_database`."""
    reference = json.loads(REFERENCE.read_text(encoding="utf-8"))

    assert declared_in_migration() == reference


def test_the_declared_rules_all_reached_the_database(migrated):
    """Объявленное в миграции против того, что легло в базу: сторожится перенос,
    а не сами таблицы.

    `upgrade` кладёт правило и его метки в трёх вложенных циклах, и
    промахнуться там есть чем: привязать источник к чужому списку, потерять
    запрет или слить метки двух правил в одно. Сравниваются четвёрки «источник,
    жанр, требуемые, запрещённые»: с парой «источник и жанр» первая из трёх
    поломок прошла бы молча.

    Чего он не ловит и ловить не должен: неверно выбранный жанр для чужой
    метки — обе стороны сравнения приходят из одного объявления. Это сторожит
    соседний `test_every_rule_matches_the_reference`."""
    stored = sorted(
        (row.source, row.name, row.required or "", row.forbidden or "",
         bool(row.alone))
        for row in migrated.execute(text(
            "SELECT r.source, g.name, r.alone, "
            "  (SELECT group_concat(m.ext_id, '|') FROM ("
            "     SELECT ext_id FROM genre_rule_mark "
            "     WHERE rule_id = r.id AND forbidden = 0 ORDER BY ext_id) m"
            "  ) AS required, "
            "  (SELECT group_concat(m.ext_id, '|') FROM ("
            "     SELECT ext_id FROM genre_rule_mark "
            "     WHERE rule_id = r.id AND forbidden = 1 ORDER BY ext_id) m"
            "  ) AS forbidden "
            "FROM genre_rule r JOIN genre g ON g.id = r.genre_id"
        ))
    )
    declared = sorted(
        (source, genre, "|".join(sorted(required)), "|".join(sorted(forbidden)),
         alone)
        for source, rules in declared_in_migration().items()
        for genre, required, forbidden, alone in rules
    )

    assert stored == declared


def test_every_rule_leads_to_an_existing_genre(migrated):
    """Правило в никуда — тихая потеря жанра: карточка приедет без него, и
    никто не заметит.

    Сравниваются два числа, а не проверяется отсутствие сирот: на пустой
    таблице сирот нет тоже."""
    joined = counted(migrated, "genre_rule r",
                     "JOIN genre g ON g.id = r.genre_id")
    assert (joined, counted(migrated, "genre_rule")) == (RULES, RULES)


def test_the_reference_can_be_rolled_back_and_laid_again(tmp_path):
    """Обратный ход этой миграции — не пустая формальность: она вставляет
    строки, и не убрав их за собой, следующий же прямой ход упирается в
    уникальность имени жанра. Полный откат до пустой базы этого не показывает —
    там строки уходят вместе с таблицами.

    Метки считаются тоже: каскад тут двухступенчатый, и осиротевшая метка
    прицепилась бы к чужому правилу — `genre_rule.id` это rowid, и SQLite
    выдаёт его повторно."""
    db_path = tmp_path / "library.db"
    alembic(db_path, "upgrade", "head")
    alembic(db_path, "downgrade", "0001")
    alembic(db_path, "upgrade", "head")

    engine = sqlalchemy.create_engine(f"sqlite:///{db_path}")
    with engine.connect() as connection:
        genres = counted(connection, "genre")
        rules = counted(connection, "genre_rule")
        marks = counted(connection, "genre_rule_mark")
    engine.dispose()
    assert (genres, rules) == (87, RULES)
    assert marks == MARKS


def test_film_and_game_sets_never_mix(migrated):
    """Кино и игры — два раздельных набора. Правило из магазина, ведущее в
    киношный жанр, значит, что при вставке перепутан набор."""
    right = counted(
        migrated, "genre_rule r",
        "JOIN genre g ON g.id = r.genre_id "
        "WHERE (r.source = 'tmdb') = (g.kind = 'film')",
    )
    assert right == RULES
