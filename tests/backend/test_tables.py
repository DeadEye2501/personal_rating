"""Объявленная схема: таблицы, индексы, ключи и ограничения."""

import pytest
from sqlalchemy import Date, DateTime, Float, Integer, Text, func, inspect, select
from sqlalchemy.exc import IntegrityError

from backend.storage.tables import metadata
from tests.conftest import MINIMAL, MOMENT, TABLES


async def counted(engine, table_name: str) -> int:
    table = metadata.tables[table_name]
    async with engine.connect() as connection:
        found = await connection.execute(select(func.count()).select_from(table))
    return found.scalar()


async def put(engine, table_name: str, **values) -> None:
    async with engine.begin() as connection:
        table = metadata.tables[table_name]
        await connection.execute(table.insert().values(**values))


async def test_every_table_from_the_spec_exists(engine):
    async with engine.connect() as connection:
        names = await connection.run_sync(
            lambda sync: set(inspect(sync).get_table_names())
        )
    assert names == TABLES


async def test_every_index_from_the_spec_exists_in_the_database(engine):
    """Индексы проверяются в поднятой базе, а не в объявлении: объявленный
    индекс до базы может и не доехать. Здесь её поднимает `metadata.create_all`
    из фикстуры; ту же схему, построенную миграцией, сторожит
    `test_migrations.py`."""
    async with engine.connect() as connection:
        built = await connection.run_sync(
            lambda sync: {
                # Имя вместе со столбцами: по одному имени индекс, переставленный
                # на другую колонку, неотличим от нужного.
                (index["name"], tuple(index["column_names"]))
                for name in TABLES
                for index in inspect(sync).get_indexes(name)
            }
        )
    assert {
        ("ix_item_kind", ("kind",)),
        ("ix_item_kind_year", ("kind", "year")),
        ("ix_rating_score", ("score",)),
        ("ix_rating_updated_at", ("updated_at",)),
        ("ix_wishlist_added_at", ("added_at",)),
        ("ix_item_genre_genre_id", ("genre_id",)),
        ("ix_item_tag_tag_id", ("tag_id",)),
        ("ix_person_credit_person_id", ("person_id",)),
        ("ix_company_credit_company_id", ("company_id",)),
    } <= built


TYPES = [
    ("item", "year", Integer), ("item", "released_at", Date),
    ("item", "synced_at", DateTime), ("item", "title", Text),
    ("rating", "score", Float), ("rating", "visual", Integer),
    ("rating", "created_at", DateTime), ("external_rating", "value", Float),
    ("tag", "position", Integer),
]


@pytest.mark.parametrize(("name", "column", "kind"), TYPES)
def test_column_types_match_the_spec(name, column, kind):
    # Объявление, а не следствие: SQLite типы колонок не навязывает, и
    # проверить их поведением нельзя — 7.5 он положит в Integer как есть.
    # Следствие видно на границе: `Item.released_at` приезжает датой, а не
    # строкой, и это сторожит `test_library.py`.
    assert isinstance(metadata.tables[name].c[column].type, kind)


REQUIRED = [
    ("item", "kind"), ("item", "source"), ("item", "source_id"),
    ("item", "title"), ("item", "synced_at"),
    ("genre", "name"), ("genre", "kind"),
    ("person", "name"), ("company", "name"),
    ("tag", "name"), ("tag", "kind"), ("tag", "position"),
]


@pytest.mark.parametrize(("name", "column"), REQUIRED)
async def test_required_columns_reject_null(engine, name, column):
    values = {key: value for key, value in MINIMAL[name].items() if key != column}
    with pytest.raises(IntegrityError):
        await put(engine, name, **values)


# Вторая строка отличается всем, чем может, кроме самого ключа: с полной
# копией расширение ключа лишней колонкой прошло бы незамеченным.
UNIQUE = [
    ("item", {}, {"title": "Другое название", "year": 2014}),
    ("genre", {}, {}),
    ("tag", {}, {"position": 7}),
    ("person", {"source": "tmdb", "source_id": "525"}, {"name": "Кристофер Р. Нолан"}),
]


@pytest.mark.parametrize(("name", "extra", "differs"), UNIQUE)
async def test_uniqueness_is_enforced_by_the_database(engine, name, extra, differs):
    """Уникальность проверяется вставкой дубля, а не чтением объявления:
    объявленное без индекса в базе ничего не запрещает."""
    await put(engine, name, **{**MINIMAL[name], **extra})
    with pytest.raises(IntegrityError):
        await put(engine, name, **{**MINIMAL[name], **extra, **differs})


COMPOSITE = [
    # Роль в ключе: один человек бывает на карточке и режиссёром, и актёром.
    ("person_credit", ("item_id", "person_id", "role")),
    ("company_credit", ("item_id", "company_id", "role")),
    # Метка в ключе правила одна: и требуемой, и запрещённой она не бывает.
    ("genre_rule_mark", ("rule_id", "ext_id")),
    # Тип содержимого в ключе: у TMDB фильмы и сериалы нумеруются порознь и
    # сталкиваются числами — `tmdb/1399` это и фильм, и «Игра престолов».
    ("removed", ("kind", "source", "source_id")),
    ("item_genre", ("item_id", "genre_id")),
    ("item_tag", ("item_id", "tag_id")),
    ("external_id", ("item_id", "source")),
    ("external_rating", ("item_id", "source")),
]


@pytest.mark.parametrize(("name", "columns"), COMPOSITE)
def test_composite_keys_keep_every_column(name, columns):
    actual = tuple(column.name for column in metadata.tables[name].primary_key)
    assert actual == columns


async def test_deleting_an_item_takes_everything_hanging_on_it(engine, stored):
    """Каскад проверяется удалением, а не объявлением: `ondelete` в схеме без
    включённого `PRAGMA foreign_keys` не делает ничего."""
    item_id = await stored("item")
    genre_id = await stored("genre")
    person_id = await stored("person")
    company_id = await stored("company")
    tag_id = await stored("tag")

    hanging = {
        "rating": {"score": 8.0, "created_at": MOMENT, "updated_at": MOMENT},
        "wishlist": {"added_at": MOMENT},
        "item_genre": {"genre_id": genre_id},
        "item_tag": {"tag_id": tag_id},
        "person_credit": {"person_id": person_id, "role": "director"},
        "company_credit": {"company_id": company_id, "role": "developer"},
        "external_id": {"source": "imdb", "value": "tt0816692"},
        "external_rating": {"source": "imdb", "value": 8.6, "fetched_at": MOMENT},
    }
    for name, values in hanging.items():
        await put(engine, name, item_id=item_id, **values)

    async with engine.begin() as connection:
        await connection.execute(
            metadata.tables["item"].delete().where(
                metadata.tables["item"].c.id == item_id
            )
        )

    for name in hanging:
        assert await counted(engine, name) == 0, name


PARENTS = [
    ("genre", "item_genre", {"genre_id": None}),
    ("genre", "genre_rule", {"source": "tmdb", "alone": False, "genre_id": None}),
    ("person", "person_credit", {"person_id": None, "role": "actor"}),
    ("company", "company_credit", {"company_id": None, "role": "publisher"}),
    ("tag", "item_tag", {"tag_id": None}),
]


@pytest.mark.parametrize(("parent", "child", "link"), PARENTS)
async def test_deleting_a_parent_takes_its_links(engine, stored, parent, child, link):
    parent_id = await stored(parent)
    values = {key: parent_id if value is None else value for key, value in link.items()}
    if "item_id" in metadata.tables[child].c:
        values["item_id"] = await stored("item")
    await put(engine, child, **values)

    table = metadata.tables[parent]
    async with engine.begin() as connection:
        await connection.execute(table.delete().where(table.c.id == parent_id))

    assert await counted(engine, child) == 0


async def test_two_namesakes_without_identifiers_both_fit(engine, stored):
    """Уникальность у человека стоит на паре «источник и его номер», не на
    имени: полные тёзки существуют, а Steam и GOG людей не отдают вовсе."""
    await stored("person")
    await stored("person")
    assert await counted(engine, "person") == 2


async def test_an_external_rating_can_say_the_source_has_none(engine, stored):
    """Пустой `value` — это ответ «у источника такой оценки нет». Отсутствие
    ответа — отсутствие строки."""
    item_id = await stored("item")
    await put(
        engine, "external_rating",
        item_id=item_id, source="rotten", value=None, fetched_at=MOMENT,
    )
    assert await counted(engine, "external_rating") == 1
