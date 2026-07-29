"""Второй файл базы: картинка по карточке."""

from datetime import datetime
from pathlib import Path

from sqlalchemy import (
    BLOB,
    Column,
    DateTime,
    Integer,
    MetaData,
    Table,
    delete,
    select,
)
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncEngine

from backend.storage.session import create_engine

metadata = MetaData()

# Ключ — карточка, а не адрес: у залитой с диска картинки адреса нет, и
# скачанный постер от залитого отличаться не должен.
poster = Table(
    "poster", metadata,
    Column("item_id", Integer, primary_key=True),
    Column("data", BLOB, nullable=False),
    Column("fetched_at", DateTime, nullable=False),
)


class PosterStore:
    """Отдельный файл рядом с основной базой: основная маленькая и часто
    пишется, картинки большие и пишутся раз. Внешних ключей к основной здесь
    нет и быть не может: между двумя файлами SQLite их не бывает."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._engine: AsyncEngine | None = None

    async def open(self) -> None:
        # Повторное открытие закрывает прежний движок: иначе он теряется
        # вместе с соединением, а на Windows незакрытый файл базы не удалить.
        await self.close()
        self._engine = create_engine(self._path)
        async with self._engine.begin() as connection:
            await connection.run_sync(metadata.create_all)

    async def close(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None

    async def put(self, item_id: int, data: bytes, now: datetime) -> None:
        statement = insert(poster).values(
            item_id=item_id, data=data, fetched_at=now
        )
        statement = statement.on_conflict_do_update(
            index_elements=[poster.c.item_id],
            set_={"data": statement.excluded.data,
                  "fetched_at": statement.excluded.fetched_at},
        )
        async with self._engine.begin() as connection:
            await connection.execute(statement)

    async def get(self, item_id: int) -> bytes | None:
        async with self._engine.connect() as connection:
            result = await connection.execute(
                select(poster.c.data).where(poster.c.item_id == item_id)
            )
            return result.scalar_one_or_none()

    async def has(self, item_id: int) -> bool:
        async with self._engine.connect() as connection:
            result = await connection.execute(
                select(poster.c.item_id).where(poster.c.item_id == item_id)
            )
            return result.one_or_none() is not None

    async def delete(self, item_id: int) -> None:
        async with self._engine.begin() as connection:
            await connection.execute(
                delete(poster).where(poster.c.item_id == item_id)
            )
