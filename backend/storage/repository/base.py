"""Общее у репозиториев: сессия и три способа с ней обойтись."""

from collections.abc import Callable

from sqlalchemy import Executable, Row
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class Repository:
    """Работа с основной базой через фабрику сессий.

    Заведено на третьей реализации, а не в ожидании первой: одинаковыми у них
    оказались и приём фабрики, и все способы сходить в базу."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def _row(self, statement: Executable) -> Row | None:
        async with self._sessions() as session:
            return (await session.execute(statement)).one_or_none()

    async def _rows(self, statement: Executable) -> list[Row]:
        async with self._sessions() as session:
            return list((await session.execute(statement)).all())

    async def _mapped(self, statement: Executable, make: Callable[[Row], object]):
        """Строки сразу в свои типы: наружу репозиторий отдаёт их, а не `Row`."""
        return [make(row) for row in await self._rows(statement)]

    async def _run(self, *statements: Executable) -> None:
        """Всё переданное — одной транзакцией: замена набора это удаление и
        вставка, и половина такой замены хуже, чем ничего."""
        async with self._sessions() as session:
            for statement in statements:
                await session.execute(statement)
            await session.commit()
