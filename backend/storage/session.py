"""Доступ к основной базе."""

from pathlib import Path

from sqlalchemy import event
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


def create_engine(path: Path) -> AsyncEngine:
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}")

    @event.listens_for(engine.sync_engine, "connect")
    def prepare_connection(dbapi_connection, _record):
        # SQLite выключает внешние ключи на каждом подключении заново.
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
        dbapi_connection.create_function("py_lower", 1, fold, deterministic=True)

    return engine


def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
