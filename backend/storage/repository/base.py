"""Общее у репозиториев: сессия и способы с ней обойтись."""

from collections.abc import Callable

from sqlalchemy import Executable, Row, Table, select
from sqlalchemy.exc import IntegrityError
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

    async def _maybe(self, statement: Executable, make: Callable[[Row], object]):
        """Одна строка в свой тип или `None`, если её нет. То же, что
        `_mapped`, для единственной: репозитории отличаются преобразователем,
        а не тем, как проверить пустоту."""
        row = await self._row(statement)
        return make(row) if row is not None else None

    async def _has_item(self, table: Table, item_id: int) -> bool:
        """Есть ли в таблице строка про эту карточку.

        Спрашивают об этом трое — закладка про себя, сводка перед удалением
        про оценку и про закладку, — и запрос у всех троих один и тот же."""
        return await self._row(
            select(table.c.item_id).where(table.c.item_id == item_id)
        ) is not None

    async def _created(self, statement: Executable, taken: Exception) -> int:
        """Вставка, возвращающая выданный базой номер.

        Занятый ключ уникальности переводится в своё исключение:
        `IntegrityError` живёт в SQLAlchemy, и пробрось мы его — знание о ней
        поехало бы вверх по слоям до самого клиента, которому туда нельзя."""
        async with self._sessions() as session:
            try:
                result = await session.execute(statement)
                await session.commit()
            except IntegrityError as error:
                # Откат делает выход из `async with`: сессия закрывается и
                # незавершённую транзакцию отматывает сама.
                raise taken from error
            return result.scalar_one()

    async def _written(self, statement: Executable, taken: Exception) -> None:
        """Правка, у которой занятый ключ уникальности — не поломка, а отказ.
        Своё исключение вместо чужого — по той же причине, что и в `_created`."""
        try:
            await self._run(statement)
        except IntegrityError as error:
            raise taken from error

    async def _run(self, *statements: Executable) -> None:
        """Всё переданное — одной транзакцией: замена набора это удаление и
        вставка, и половина такой замены хуже, чем ничего."""
        async with self._sessions() as session:
            for statement in statements:
                await session.execute(statement)
            await session.commit()
