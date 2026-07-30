"""Доступ к основной базе."""

from pathlib import Path

from sqlalchemy import ColumnElement, event, func
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def fold(value: str | None) -> str | None:
    """Регистр для сравнения названий. Встроенный в SQLite lower() умеет
    только ASCII и «Ведьмак» оставляет как есть — а Python приводит его
    правильно. Поэтому сравниваем обе стороны одними правилами."""
    return value.lower() if value is not None else None


def folded(column: ColumnElement) -> ColumnElement[str]:
    """Та же `fold`, но на стороне базы. Сравнивать надо обе стороны одними
    правилами, поэтому и живут они рядом."""
    return func.py_lower(column)


def prepare_connection(dbapi_connection) -> None:
    """Соединение к нашей базе. И внешние ключи, и своё сравнение регистра
    живут на соединении, а не на базе: SQLite выключает первые и забывает
    второе на каждом новом подключении. Зовут отсюда двое — движок приложения
    и Alembic, который ходит своим, синхронным."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    # Обычный журнал заставляет читателя ждать писателя, а у ленты это обычное
    # положение дел: страница читает пятьдесят карточек, обложки пишутся по мере
    # приезда, человек в это же время ставит оценку. `busy_timeout` не ставим —
    # драйвер уже даёт 5000 мс, и повтор выглядел бы починкой, ничего не меняя.
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()
    dbapi_connection.create_function("py_lower", 1, fold, deterministic=True)


def create_engine(path: Path) -> AsyncEngine:
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}")

    @event.listens_for(engine.sync_engine, "connect")
    def prepare(dbapi_connection, _record):
        prepare_connection(dbapi_connection)

    return engine


def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
