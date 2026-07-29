"""Общее у репозиториев: сессия и три способа с ней обойтись."""

from sqlalchemy import Executable, Row
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class Repository:
    """Работа с основной базой через фабрику сессий.

    Заведено на третьей реализации, а не в ожидании первой: одинаковыми у них
    оказались и приём фабрики, и все три способа сходить в базу."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def _row(self, statement: Executable) -> Row | None:
        async with self._sessions() as session:
            return (await session.execute(statement)).one_or_none()

    async def _rows(self, statement: Executable) -> list[Row]:
        async with self._sessions() as session:
            return list((await session.execute(statement)).all())

    async def _run(self, statement: Executable) -> None:
        async with self._sessions() as session:
            await session.execute(statement)
            await session.commit()
