"""Чем карточка известна чужим источникам."""

from datetime import datetime, timedelta

from sqlalchemy import select

from backend.model import ExternalId, ExternalRating, IdSource, RatingSource
from backend.storage.repository.base import Repository
from backend.storage.statements import upserting
from backend.storage.tables import external_id as external_id_table
from backend.storage.tables import external_rating as external_rating_table

# Срок годности считается от `fetched_at`, а не хранится полем: политику тогда
# можно менять, не трогая базу.
VALUE_TTL = timedelta(days=30)
EMPTY_TTL = timedelta(days=7)


class ExternalIdTaken(Exception):
    """Такой внешний идентификатор уже принадлежит другой карточке."""


def _to_external_id(row) -> ExternalId:
    return ExternalId(source=IdSource(row.source), value=row.value)


def _to_external_rating(row) -> ExternalRating:
    return ExternalRating(
        source=RatingSource(row.source), value=row.value, fetched_at=row.fetched_at
    )


class ExternalIdsRepository(Repository):
    async def put(self, item_id: int, external: ExternalId) -> None:
        # Разрешение конфликта целит в первичный ключ, поэтому
        # UNIQUE (source, value) сюда доезжает нетронутым — и занятый чужой
        # карточкой идентификатор всё ещё поднимает отказ.
        await self._written(
            upserting(
                external_id_table,
                {"item_id": item_id, "source": external.source,
                 "value": external.value},
                [external_id_table.c.item_id, external_id_table.c.source],
            ),
            ExternalIdTaken(f"{external.source}:{external.value} уже занят"),
        )

    async def ids_of(self, item_id: int) -> list[ExternalId]:
        return await self._mapped(
            select(external_id_table)
            .where(external_id_table.c.item_id == item_id)
            .order_by(external_id_table.c.source),
            _to_external_id,
        )

    async def find_item(self, source: IdSource, value: str) -> int | None:
        return await self._maybe(
            select(external_id_table.c.item_id).where(
                external_id_table.c.source == source,
                external_id_table.c.value == value,
            ),
            lambda row: row.item_id,
        )


class ExternalRatingsRepository(Repository):
    async def record(self, item_id: int, rating: ExternalRating) -> None:
        """Пишем и находку, и честное «у источника нет». Отказ сюда не
        попадает вовсе: на входе `ExternalRating`, а `Refusal` в него не
        превратить."""
        await self._run(
            upserting(
                external_rating_table,
                {"item_id": item_id, "source": rating.source,
                 "value": rating.value, "fetched_at": rating.fetched_at},
                [external_rating_table.c.item_id,
                 external_rating_table.c.source],
            )
        )

    async def ratings_of(self, item_id: int) -> list[ExternalRating]:
        return await self._mapped(
            select(external_rating_table)
            .where(external_rating_table.c.item_id == item_id)
            .order_by(external_rating_table.c.source),
            _to_external_rating,
        )

    async def stale_sources(self, item_id: int, wanted: list[RatingSource],
                            now: datetime) -> list[RatingSource]:
        """У кого спрашивать: у тех, кого не спрашивали вовсе, и у тех, чей
        ответ протух. Пустой ответ протухает быстрее значения."""
        known = {r.source: r for r in await self.ratings_of(item_id)}

        stale = []
        for source in wanted:
            stored = known.get(source)
            if stored is None:
                stale.append(source)
                continue
            ttl = VALUE_TTL if stored.value is not None else EMPTY_TTL
            if now - stored.fetched_at > ttl:
                stale.append(source)
        return stale
