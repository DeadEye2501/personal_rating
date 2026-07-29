"""Общее для тестов: временные база и хранилище, фикстуры и минимальные строки."""

import io
from datetime import datetime

import pytest
import sqlalchemy
from PIL import Image

from backend.model import Item, Kind, Source
from backend.storage.posters import PosterStore
from backend.storage.repository.library import LibraryRepository
from backend.storage.session import (
    create_engine,
    prepare_connection,
    session_factory,
)
from backend.storage.tables import metadata
from tests.alembic_runner import alembic

# Момент и момент позже. Заведённые в каждом модуле заново, они расходились
# значениями, ничего этим не проверяя. Важен только порядок: где нужен
# определённый промежуток, тест берёт `MOMENT + timedelta(...)` и говорит это
# вслух.
MOMENT = datetime(2026, 7, 29, 12, 0)
LATER = datetime(2026, 7, 30, 12, 0)

# Байты «картинки»: подпись PNG и набивка. Обрабатывать её никто не пытается,
# хранилищу постеров важно только то, что байты вернулись теми же.
PICTURE = b"\x89PNG\r\n\x1a\n" + b"0" * 512


def picture(width: int, height: int, fmt: str = "PNG") -> bytes:
    """Настоящая картинка заданного размера. Размер обязателен: там, где эта
    картинка нужна, он и есть предмет проверки."""
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (10, 20, 30)).save(buffer, format=fmt)
    return buffer.getvalue()


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
    приложения с базой.

    Соединение готовится так же, как у приложения, — с внешними ключами:
    иначе тесты смотрели бы на базу, которой в работе не бывает."""
    db_path = tmp_path / "library.db"
    alembic(db_path, "upgrade", "head")
    engine = sqlalchemy.create_engine(f"sqlite:///{db_path}")
    sqlalchemy.event.listen(
        engine, "connect", lambda dbapi, _record: prepare_connection(dbapi)
    )
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
async def posters(tmp_path):
    """Хранилище постеров на прогон: свой файл, отдельный от основной базы."""
    store = PosterStore(tmp_path / "posters.db")
    await store.open()
    yield store
    await store.close()


@pytest.fixture
async def card(sessions):
    """Заводит карточку через репозиторий и отдаёт её идентификатор: всему,
    что вешается на карточку, сперва нужна она сама."""

    async def make(kind: Kind = Kind.MOVIE, source_id: str = "1",
                   title: str = "карточка") -> int:
        return await LibraryRepository(sessions).create(
            Item(id=0, kind=kind, source=Source.TMDB, source_id=source_id,
                 title=title, synced_at=MOMENT)
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
