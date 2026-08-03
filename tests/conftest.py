"""Фикстуры тестов и поверхность общего.

Подставной внешний мир живёт в `tests/fakes.py`, строители данных — в
`tests/builders.py`, сборка объектов бэкенда — в `tests/wiring.py`. Отсюда они
переэкспортируются: `conftest` и так читают все тесты, и второй адрес того же
помощника означал бы два способа его найти. Исключение одно — запуск миграций
из `tests/alembic_runner.py`: его берут напрямую, и переэкспорта у него нет."""


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
    recorded,
)
from tests.fakes import (
    FakeCatalog,
    FakeClient,
    FakeClock,
    FakeSearch,
    FakeSources,
    capture,
    counting,
    responding,
    unreachable,
)
from tests.wiring import POSTER_SOURCES, card_parts, poster_service

# Здесь только переэкспорт. Имя, приехавшее от соседа и не нужное самому
# `conftest`, без списка `ruff` объявит неиспользуемым импортом — так держится
# большая часть правила. На тех, которыми модуль пользуется сам (`MOMENT`,
# `an_item`), проверка молчит, и правило держит этот абзац: локальные имена —
# фикстуры, `RATED`, `TABLES` — сюда не пишем.
__all__ = [
    "LATER",
    "MOMENT",
    "PICTURE",
    "POSTER",
    "POSTER_SOURCES",
    "FakeCatalog",
    "FakeClient",
    "FakeClock",
    "FakeSearch",
    "FakeSources",
    "an_item",
    "capture",
    "card_parts",
    "counting",
    "hit",
    "picture",
    "poster_service",
    "rated",
    "recorded",
    "responding",
    "unreachable",
]

# Номера жанров из фикстуры `reference`. Карточке их ставят прямо, а не через
# справочник: там, где предмет проверки — фильтр, лента или показ, справочник
# только шум.
ACTION, ADVENTURE, DRAMA = 1, 2, 3

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
    """Два киножанра с правилами к ним. Два, а не один: с одним нельзя
    проверить, что чужой жанр не затирает выбранный руками — дополнять было бы
    нечем."""
    await seed(
        engine,
        "INSERT INTO genre (id, name, kind) VALUES "
        "(1, 'фантастика', 'film'), (2, 'приключения', 'film')",
        "INSERT INTO genre_rule (id, source, genre_id, alone) VALUES "
        "(1, 'tmdb', 1, 0), (2, 'tmdb', 2, 0)",
        "INSERT INTO genre_rule_mark (rule_id, ext_id, forbidden) VALUES "
        "(1, '878', 0), (2, '12', 0)",
    )


async def seed(engine, *statements: str) -> None:
    """Сырые строки прямо в базу. Так кладётся справочник жанров: миграцией его
    в базу из объявлений не притащить, а у каждого теста он свой — набор
    соответствий и есть предмет проверки."""
    async with engine.begin() as connection:
        for statement in statements:
            await connection.execute(sqlalchemy.text(statement))


# Список из спеки, а не из `metadata`: он и есть ожидаемое. Взятый из кода, он
# совпал бы с ним при любой пропаже таблицы.
TABLES = {
    "item", "genre", "genre_rule", "genre_rule_mark", "item_genre",
    "person", "person_credit", "company", "company_credit",
    "external_id", "external_rating",
    "rating", "tag", "item_tag", "wishlist", "removed",
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

    Тесты не зависят от миграции: проверяется разрешение меток, а не содержимое
    справочника — его сторожит `test_genre_reference.py`. Набор маленький и
    нарочно включает сборный 10759 — одну метку, ведущую в два наших жанра
    двумя правилами, — и по строке на каждое чужое пространство: без правила
    `gog` «отвергнутый слаг» и «совсем новый жанр» оказались бы одним и тем же
    случаем, потому что самого пространства в справочнике не было бы вовсе."""
    await seed(
        engine,
        "INSERT INTO genre (id, name, kind) VALUES "
        "(1, 'Боевик', 'film'), (2, 'Приключения', 'film'), "
        "(3, 'Драма', 'film'), (4, 'ролевая', 'game')",
        "INSERT INTO genre_rule (id, source, genre_id, alone) VALUES "
        "(1, 'tmdb', 1, 0), (2, 'tmdb', 2, 0), (3, 'tmdb', 3, 0), "
        "(4, 'tmdb', 1, 0), (5, 'tmdb', 2, 0), "
        "(6, 'steam', 4, 0), (7, 'gog', 4, 0)",
        "INSERT INTO genre_rule_mark (rule_id, ext_id, forbidden) VALUES "
        "(1, '28', 0), (2, '12', 0), (3, '18', 0), "
        "(4, '10759', 0), (5, '10759', 0), "
        "(6, '3', 0), (7, 'rpg', 0)",
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
