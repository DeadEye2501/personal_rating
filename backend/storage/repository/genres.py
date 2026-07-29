"""Жанры карточки и разрешение чужих идентификаторов в свои."""

import logging

from sqlalchemy import Select, delete, select
from sqlalchemy.dialects.sqlite import insert

from backend.model import Genre, GenreKind, GenreSource
from backend.storage.repository.base import Repository
from backend.storage.tables import genre as genre_table
from backend.storage.tables import genre_map as genre_map_table
from backend.storage.tables import item_genre as item_genre_table

logger = logging.getLogger(__name__)


def _to_genre(row) -> Genre:
    return Genre(id=row.id, name=row.name, kind=GenreKind(row.kind))


class GenresRepository(Repository):
    async def _genres(self, statement: Select) -> list[Genre]:
        return await self._mapped(statement, _to_genre)

    async def resolve(self, source: GenreSource, ext_ids: list[str]) -> list[int]:
        """Внешние идентификаторы в свои. Сборный разворачивается в два,
        незнакомый попадает в лог: имена в справочнике наши, а заводить жанр
        на лету нельзя."""
        if not ext_ids:
            return []

        rows = await self._rows(
            select(genre_map_table.c.ext_id, genre_map_table.c.genre_id)
            .where(
                genre_map_table.c.source == source,
                genre_map_table.c.ext_id.in_(ext_ids),
            )
        )

        known: set[str] = set()
        resolved: list[int] = []
        for row in rows:
            known.add(row.ext_id)
            if row.genre_id not in resolved:
                resolved.append(row.genre_id)

        for ext_id in ext_ids:
            if ext_id not in known:
                logger.warning(
                    "неизвестный жанр: источник %s, идентификатор %s", source, ext_id
                )
        return resolved

    async def set_for_item(self, item_id: int, genre_ids: list[int]) -> None:
        """Набор жанров заменяется целиком: пришедшее из источника — это весь
        список, а не добавка к прежнему."""
        cleared = delete(item_genre_table).where(
            item_genre_table.c.item_id == item_id
        )
        if not genre_ids:
            await self._run(cleared)
            return
        await self._run(
            cleared,
            insert(item_genre_table)
            .values([{"item_id": item_id, "genre_id": genre_id}
                     for genre_id in genre_ids])
            .on_conflict_do_nothing(),
        )

    async def genres_of(self, item_id: int) -> list[Genre]:
        return await self._genres(
            select(genre_table)
            .join(item_genre_table, item_genre_table.c.genre_id == genre_table.c.id)
            .where(item_genre_table.c.item_id == item_id)
            .order_by(genre_table.c.name)
        )

    async def list_for_kind(self, kind: GenreKind) -> list[Genre]:
        """Наборов жанров два, и зовут их `film` и `game`, а не `movie` и
        `game`: `Kind.MOVIE`, переданный сюда по ошибке, вернёт пустой список,
        а не киношные жанры."""
        return await self._genres(
            select(genre_table)
            .where(genre_table.c.kind == kind)
            .order_by(genre_table.c.name)
        )
