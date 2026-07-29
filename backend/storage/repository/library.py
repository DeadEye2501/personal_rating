"""Карточки библиотеки."""

from sqlalchemy import Row, Select, func, select
from sqlalchemy.exc import IntegrityError

from backend.model import Item, Kind, Source
from backend.storage.repository.base import Repository
from backend.storage.session import fold
from backend.storage.tables import item as item_table


class ItemExists(Exception):
    """Пара (source, source_id) уже занята другой карточкой."""


_FIELDS = (
    "kind", "source", "source_id", "title", "original_title", "year",
    "released_at", "synopsis", "poster_url", "runtime", "seasons_count",
    "episodes_count", "synced_at",
)


def _values(item: Item) -> dict:
    """Карточка в вид для вставки. `id` не берётся: его выдаёт база.

    Перечисления не переводятся в строку по пути: они `StrEnum`, то есть уже
    строки, и в колонку ложатся своим значением."""
    return {name: getattr(item, name) for name in _FIELDS}


def _to_item(row: Row) -> Item:
    """Строка базы в тип границы слоёв.

    Пустой текст отдаётся пустой строкой, а не `None`: карточку правит и
    человек, и в его строке колонка бывает пустой — а в интерфейс `None`
    уехало бы словом «None»."""
    return Item(
        id=row.id,
        kind=Kind(row.kind),
        source=Source(row.source),
        source_id=row.source_id,
        title=row.title,
        synced_at=row.synced_at,
        original_title=row.original_title or "",
        year=row.year,
        released_at=row.released_at,
        synopsis=row.synopsis or "",
        poster_url=row.poster_url or "",
        runtime=row.runtime,
        seasons_count=row.seasons_count,
        episodes_count=row.episodes_count,
    )


class LibraryRepository(Repository):
    async def _one(self, statement: Select) -> Item | None:
        row = await self._row(statement)
        return _to_item(row) if row else None

    async def _many(self, statement: Select) -> list[Item]:
        return [_to_item(row) for row in await self._rows(statement)]

    async def create(self, item: Item) -> int:
        async with self._sessions() as session:
            try:
                result = await session.execute(
                    item_table.insert()
                    .values(**_values(item))
                    .returning(item_table.c.id)
                )
                await session.commit()
            except IntegrityError as error:
                # Откат делает выход из `async with`: сессия закрывается и
                # незавершённую транзакцию отматывает сама.
                raise ItemExists(
                    f"{item.source}:{item.source_id} уже в библиотеке"
                ) from error
            return result.scalar_one()

    async def get(self, item_id: int) -> Item | None:
        return await self._one(select(item_table).where(item_table.c.id == item_id))

    async def find_by_source(self, source: Source, source_id: str) -> Item | None:
        return await self._one(
            select(item_table).where(
                item_table.c.source == source,
                item_table.c.source_id == source_id,
            )
        )

    async def list_by_kind(self, kind: Kind, limit: int, offset: int) -> list[Item]:
        """Порядок по названию — решение этого плана, а не спеки: у разделов
        свои порядки, и они лягут в запросы сервисного слоя. Здесь нужен
        любой устойчивый, чтобы порции не перемешивались между запросами."""
        return await self._many(
            select(item_table)
            .where(item_table.c.kind == kind)
            .order_by(item_table.c.title)
            .limit(limit)
            .offset(offset)
        )

    async def find_by_title(self, kind: Kind, title: str) -> list[Item]:
        """Для предупреждения о совпадении: сравнение по обоим названиям и
        только внутри своего типа содержимого.

        Обе стороны приводятся одной и той же функцией: встроенный в SQLite
        lower() умеет только ASCII, и с ним русские названия не совпали бы
        никогда."""
        needle = fold(title.strip())
        return await self._many(
            select(item_table).where(
                item_table.c.kind == kind,
                (func.py_lower(item_table.c.title) == needle)
                | (func.py_lower(item_table.c.original_title) == needle),
            )
        )
