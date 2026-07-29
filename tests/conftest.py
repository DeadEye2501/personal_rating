from datetime import datetime

import pytest
import sqlalchemy

from backend.model import Item, Kind, Source
from backend.storage.repository.library import LibraryRepository
from backend.storage.session import create_engine, session_factory
from backend.storage.tables import metadata
from tests.alembic_runner import alembic

MOMENT = datetime(2026, 7, 29, 12, 0)

# Список из спеки, а не из `metadata`: он и есть ожидаемое. Взятый из кода, он
# совпал бы с ним при любой пропаже таблицы.
TABLES = {
    "item", "genre", "genre_map", "item_genre",
    "person", "person_credit", "company", "company_credit",
    "external_id", "external_rating",
    "rating", "tag", "item_tag", "wishlist",
}

# Минимально допустимая строка каждой таблицы: только обязательные колонки.
# Отсюда же берутся значения, когда нужно проверить отказ на пропущенном.
MINIMAL = {
    "item": {"kind": "movie", "source": "tmdb", "source_id": "157336",
             "title": "Интерстеллар", "synced_at": MOMENT},
    "genre": {"name": "Драма", "kind": "film"},
    "person": {"name": "Кристофер Нолан"},
    "company": {"name": "CD Projekt RED"},
    "tag": {"name": "любимое", "kind": "movie", "position": 1},
}


@pytest.fixture
def migrated(tmp_path):
    """Соединение с базой, поднятой миграциями. Синхронное: миграции идут
    синхронным драйвером, и проверяется здесь их результат, а не работа
    приложения с базой."""
    db_path = tmp_path / "library.db"
    alembic(db_path, "upgrade", "head")
    engine = sqlalchemy.create_engine(f"sqlite:///{db_path}")
    with engine.connect() as connection:
        yield connection
    engine.dispose()


@pytest.fixture
async def engine(tmp_path):
    """Своя база на каждый тест: файл, а не :memory:, — проверяется в том числе
    отсутствие внешних ключей между двумя файлами базы."""
    made = create_engine(tmp_path / "library.db")
    async with made.begin() as connection:
        await connection.run_sync(metadata.create_all)
    yield made
    await made.dispose()


@pytest.fixture
async def sessions(engine):
    """Фабрика сессий поверх тестовой базы: репозитории принимают её, а не
    движок."""
    return session_factory(engine)


@pytest.fixture
async def card(sessions):
    """Заводит карточку через репозиторий и отдаёт её идентификатор: всему,
    что вешается на карточку, сперва нужна она сама."""

    async def make(kind: Kind = Kind.MOVIE, source_id: str = "1") -> int:
        return await LibraryRepository(sessions).create(
            Item(id=0, kind=kind, source=Source.TMDB, source_id=source_id,
                 title="карточка", synced_at=MOMENT)
        )

    return make


@pytest.fixture
async def stored(engine):
    """Кладёт минимальную строку в таблицу и отдаёт её идентификатор."""

    async def put(name: str, **values) -> int:
        table = metadata.tables[name]
        async with engine.begin() as connection:
            done = await connection.execute(
                table.insert().values(**{**MINIMAL[name], **values})
            )
        return done.inserted_primary_key[0]

    return put
