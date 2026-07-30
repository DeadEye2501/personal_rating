"""Фикстуры тестов и поверхность общего.

Подставные клиенты живут в `tests/fakes.py`, строители данных — в
`tests/builders.py`, сборка объектов бэкенда — в `tests/wiring.py`. Отсюда они
переэкспортируются: `conftest` и так читают все тесты, и второй адрес того же
помощника означал бы два способа его найти."""


import httpx
import pytest
import sqlalchemy

from backend.model import (
    Feed,
    Filters,
    Kind,
    Order,
    Section,
    Sort,
)
from backend.storage.posters import PosterStore
from backend.storage.repository.library import LibraryRepository
from backend.storage.repository.sections import SectionsRepository
from backend.storage.session import (
    create_engine,
    prepare_connection,
    session_factory,
)
from backend.storage.tables import metadata
from tests.alembic_runner import alembic

from tests.builders import (
    LATER,
    MOMENT,
    PICTURE,
    POSTER,
    an_item,
    hit,
    picture,
    rated,
)
from tests.fakes import FakeCatalog, FakeClient, FakeSources
from tests.wiring import POSTER_SOURCES, card_parts, poster_service

__all__ = [
    "LATER",
    "MINIMAL",
    "MOMENT",
    "PICTURE",
    "POSTER",
    "POSTER_SOURCES",
    "RATED",
    "TABLES",
    "WANTED",
    "FakeCatalog",
    "FakeClient",
    "FakeSources",
    "an_item",
    "card_parts",
    "film_genres",
    "hit",
    "ours",
    "picture",
    "poster_service",
    "rated",
    "seed",
]

# Вопрос ленты, от которого отталкиваются проверки разделов: оценённое кино по
# убыванию оценки. Что именно проверяет тест, он меняет через `replace`, и в
# вызове видно только это.
RATED = Feed(Section.RATED, Kind.MOVIE, Filters(), Order(Sort.SCORE))
WANTED = Feed(Section.WISHLIST, Kind.MOVIE, Filters(), Order(Sort.ADDED_AT))


def ours(caplog) -> list[str]:
    """Записи в лог, сделанные нашим кодом. Чужие не в счёт: драйвер базы на
    уровне отладки говорит за каждый запрос."""
    return [
        record.getMessage()
        for record in caplog.records
        if record.name.startswith("backend")
    ]


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


def capture(*, content: bytes | None = None, status: int = 200):
    """Запоминает ушедшее на провод: проверять надо запрос, а не намерение.

    `content` — тело ответа байтами, когда запрашивают картинку: пустой JSON
    вместо неё сам стал бы отказом, и проверка адреса на него не добралась бы.
    `status` нужен там, где проверяется отказ: тело при этом всё равно
    возвращается, но до него дело не доходит."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if content is None:
            return httpx.Response(status, json={})
        return httpx.Response(status, content=content)

    return httpx.MockTransport(handler), seen


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
async def sections(sessions):
    """Запросы разделов: их спрашивают и лента, и гистограмма."""
    return SectionsRepository(sessions)


@pytest.fixture
async def reference(engine):
    """Справочник жанров, засеянный руками.

    Тесты не зависят от миграции: проверяется разрешение идентификаторов, а не
    содержимое справочника — его сторожит `test_genre_reference.py`. Набор
    маленький и нарочно включает сборный 10759 — один внешний идентификатор,
    разворачивающийся в два наших жанра, — и по одной строке на каждое чужое
    пространство: без строки `gog` «отвергнутый слаг» и «совсем новый жанр»
    оказались бы одним и тем же случаем, потому что самого пространства в
    справочнике не было бы вовсе."""
    await seed(
        engine,
        "INSERT INTO genre (id, name, kind) VALUES "
        "(1, 'Боевик', 'film'), (2, 'Приключения', 'film'), "
        "(3, 'Драма', 'film'), (4, 'ролевая', 'game')",
        "INSERT INTO genre_map (source, ext_id, genre_id) VALUES "
        "('tmdb', '28', 1), ('tmdb', '12', 2), ('tmdb', '18', 3), "
        "('tmdb', '10759', 1), ('tmdb', '10759', 2), "
        "('steam', '3', 4), ('gog', 'rpg', 4), ('gog_tag', 'story-rich', 3)",
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
            an_item(source_id, title, kind=kind)
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
