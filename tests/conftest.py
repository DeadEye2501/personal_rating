"""Общее для тестов: временные база и хранилище, фикстуры и минимальные строки."""

import io
from datetime import datetime

import httpx
import pytest
import sqlalchemy
from PIL import Image

from backend.model import Item, Kind, Source
from backend.service.posters import PosterService
from backend.sources.http import SourceHttp
from backend.storage.posters import PosterStore
from backend.storage.repository.credits import companies, people
from backend.storage.repository.external import (
    ExternalIdsRepository,
    ExternalRatingsRepository,
)
from backend.storage.repository.genres import GenresRepository
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

# Источники, у которых бывает обложка: у ручной карточки её скачивать негде.
POSTER_SOURCES = (Source.TMDB, Source.STEAM, Source.GOG)

# Байты «картинки»: подпись PNG и набивка. Обрабатывать её никто не пытается,
# хранилищу постеров важно только то, что байты вернулись теми же.
PICTURE = b"\x89PNG\r\n\x1a\n" + b"0" * 512


def ours(caplog) -> list[str]:
    """Записи в лог, сделанные нашим кодом. Чужие не в счёт: драйвер базы на
    уровне отладки говорит за каждый запрос."""
    return [
        record.getMessage()
        for record in caplog.records
        if record.name.startswith("backend")
    ]


def card_parts(sessions, store: PosterStore,
               transport: httpx.MockTransport) -> dict:
    """Репозитории одной карточки и сервис обложек: и писателя, и привязку
    собирают из одного и того же — они наследники `CardParts`."""
    return {
        "library": LibraryRepository(sessions),
        "genres": GenresRepository(sessions),
        "people": people(sessions),
        "companies": companies(sessions),
        "ids": ExternalIdsRepository(sessions),
        "ratings": ExternalRatingsRepository(sessions),
        "posters": poster_service(store, transport),
    }


def an_item(source_id: str, title: str, **fields) -> Item:
    """Незаписанная карточка: опознание аргументами, остальное по вкусу теста.

    Умолчания — фильм от TMDB: таких проверок больше всего, а `Item` требует
    шесть полей, и повторять их в каждом тесте значит спрятать среди них то
    одно, ради которого тест написан."""
    return Item(
        id=0,
        kind=fields.pop("kind", Kind.MOVIE),
        source=fields.pop("source", Source.TMDB),
        source_id=source_id,
        title=title,
        synced_at=fields.pop("synced_at", MOMENT),
        **fields,
    )


async def film_genres(engine) -> None:
    """Два киножанра со соответствиями к ним. Два, а не один: с одним нельзя
    проверить, что чужой жанр не затирает выбранный руками — дополнять было бы
    нечем."""
    await seed(
        engine,
        "INSERT INTO genre (id, name, kind) VALUES "
        "(1, 'фантастика', 'film'), (2, 'приключения', 'film')",
        "INSERT INTO genre_map (source, ext_id, genre_id) VALUES "
        "('tmdb', '878', 1), ('tmdb', '12', 2)",
    )


async def seed(engine, *statements: str) -> None:
    """Сырые строки прямо в базу. Так кладётся справочник жанров: миграцией его
    в базу из объявлений не притащить, а у каждого теста он свой — набор
    соответствий и есть предмет проверки."""
    async with engine.begin() as connection:
        for statement in statements:
            await connection.execute(sqlalchemy.text(statement))


def poster_service(store: PosterStore,
                   transport: httpx.MockTransport) -> PosterService:
    """Сервис обложек с одним транспортом на все три источника. Где важно, кого
    именно спросили, тест собирает клиентов сам."""
    clients = {source: SourceHttp(f"cdn:{source}", transport=transport)
               for source in POSTER_SOURCES}
    return PosterService(clients, store)


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
async def reference(engine):
    """Справочник жанров, засеянный руками.

    Тесты не зависят от миграции: проверяется разрешение идентификаторов, а не
    содержимое справочника — его сторожит `test_genre_reference.py`. Набор
    маленький и нарочно включает сборный 10759 — один внешний идентификатор,
    разворачивающийся в два наших жанра."""
    await seed(
        engine,
        "INSERT INTO genre (id, name, kind) VALUES "
        "(1, 'Боевик', 'film'), (2, 'Приключения', 'film'), "
        "(3, 'Драма', 'film'), (4, 'ролевая', 'game')",
        "INSERT INTO genre_map (source, ext_id, genre_id) VALUES "
        "('tmdb', '28', 1), ('tmdb', '12', 2), ('tmdb', '18', 3), "
        "('tmdb', '10759', 1), ('tmdb', '10759', 2), "
        "('steam', '3', 4)",
    )


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
