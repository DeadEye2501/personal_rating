"""Движок базы, сессии и настройки соединения."""

import pytest
from sqlalchemy import text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from backend.storage.session import create_engine, fold, session_factory


@pytest.fixture
async def bare_engine(tmp_path):
    made = create_engine(tmp_path / "library.db")
    yield made
    await made.dispose()


async def test_foreign_keys_are_enabled_on_every_connection(bare_engine):
    """PRAGMA живёт на соединении, а не на базе, и SQLite сбрасывает её на
    каждом новом. Проверять на одном соединении бесполезно: `first_connect`
    вместо `connect` прошёл бы незамеченным, а каскадное удаление сломалось бы
    молча на втором запросе из пула."""
    async with bare_engine.connect() as first, bare_engine.connect() as second:
        for connection in (first, second):
            result = await connection.execute(text("PRAGMA foreign_keys"))
            assert result.scalar() == 1


async def test_the_database_keeps_a_write_ahead_log(bare_engine, tmp_path):
    """Ради этого WAL и включён: с обычным журналом читатель и писатель запирают
    друг друга, а у ленты это обычное положение дел — страница читает пятьдесят
    карточек, обложки пишутся по мере приезда, человек в это же время ставит
    оценку.

    Смотрим на файл рядом с базой, а не на `PRAGMA journal_mode`: прочитать
    настройку и сравнить с ожидаемой значило бы повторить строку кода. Прямое
    следствие — незапертый писатель — на этом драйвере не проверить: pysqlite не
    открывает транзакцию на `SELECT`, и читательскую блокировку не удержать без
    отдельной обвязки, а без неё оба режима отвечают одинаково."""
    async with bare_engine.begin() as connection:
        await connection.execute(text("CREATE TABLE sample (title TEXT)"))
        await connection.execute(text("INSERT INTO sample VALUES ('Ведьмак')"))

        assert (tmp_path / "library.db-wal").exists(), \
            "журнала упреждающей записи нет — база в обычном режиме"


async def test_case_folding_is_registered_on_every_connection(bare_engine):
    async with bare_engine.connect() as first, bare_engine.connect() as second:
        for connection in (first, second):
            result = await connection.execute(text("SELECT py_lower('ВЕДЬМАК')"))
            assert result.scalar() == "ведьмак"


async def test_case_folding_handles_cyrillic(bare_engine):
    """Встроенный в SQLite lower() умеет только ASCII, поэтому сравнение
    названий держится на своей функции."""
    async with bare_engine.connect() as connection:
        result = await connection.execute(text("SELECT py_lower('Ведьмак')"))
        assert result.scalar() == "ведьмак"


def test_folding_passes_none_through():
    # NULL приезжает из базы как None: без этой ветки сравнение падало бы на
    # карточке без оригинального названия.
    assert fold(None) is None
    assert fold("Ведьмак") == "ведьмак"


async def test_case_folding_works_inside_an_index(bare_engine):
    """`deterministic=True` — не украшение: без него SQLite отказывается
    строить индекс по выражению, и падает миграция, а не тест."""
    async with bare_engine.begin() as connection:
        await connection.execute(text("CREATE TABLE sample (title TEXT)"))
        await connection.execute(
            text("CREATE INDEX sample_title ON sample (py_lower(title))")
        )


async def test_engine_creates_missing_folders(tmp_path):
    target = tmp_path / "data" / "personal" / "library.db"
    made = create_engine(target)
    async with made.connect():
        pass
    await made.dispose()
    assert target.exists()


class Base(DeclarativeBase):
    pass


class Note(Base):
    __tablename__ = "note"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]


async def test_sessions_do_not_expire_objects_on_commit(bare_engine):
    """`expire_on_commit=False` — не украшение: с ним объект после коммита
    остаётся годным, а без него первое же обращение к полю лезет в базу за
    обновлением и падает `MissingGreenlet` — из чужого потока в asyncio так
    нельзя."""
    async with bare_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with session_factory(bare_engine)() as session:
        note = Note(title="Ведьмак")
        session.add(note)
        await session.commit()
        assert note.title == "Ведьмак"
