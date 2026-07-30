"""Жанры в базе: свои, и чужие метки, ведущие к ним."""

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert

from backend.model import Genre, GenreKind, GenreSource
from backend.storage.repository.base import Repository
from backend.storage.rows import grouped, to_genre
from backend.storage.statements import clearing
from backend.storage.tables import genre as genre_table
from backend.storage.tables import genre_map as genre_map_table
from backend.storage.tables import item_genre as item_genre_table
from backend.unique import unique


class GenresRepository(Repository):
    async def resolve(self, source: GenreSource, ext_ids: list[str]) -> list[int]:
        """Внешние идентификаторы в свои.

        Сборный разворачивается в два. Незнакомый молча отбрасывается: имена в
        справочнике наши, сборный жанр автоматически не разложить, а пополняют
        справочник руками. Карточка приезжает без этого жанра, и всё."""
        if not ext_ids:
            return []

        rows = await self._rows(
            select(genre_map_table.c.genre_id)
            .where(
                genre_map_table.c.source == source,
                genre_map_table.c.ext_id.in_(ext_ids),
            )
        )

        # Порядок сохраняется: сборный жанр разворачивается в два, и оба должны
        # прийти в том порядке, в каком лежат в справочнике.
        return unique(row.genre_id for row in rows)

    async def index(self, source: GenreSource) -> dict[str, tuple[Genre, ...]]:
        """Соответствия одного пространства целиком.

        В выдаче поиска жанры приходят голыми идентификаторами, и разворачивать
        их по кандидату значит запрос на кандидата. Один сборный идентификатор
        разворачивается в несколько жанров — отсюда кортеж, а не жанр.

        Пространство, а не источник карточки: у магазина их два, жанры и теги,
        и нумеруются они порознь — `9` у Steam это и «Гонки», и «Стратегия»."""
        rows = await self._rows(
            select(genre_map_table.c.ext_id, genre_table)
            .join(genre_table, genre_table.c.id == genre_map_table.c.genre_id)
            .where(genre_map_table.c.source == source)
            .order_by(genre_table.c.name)
        )
        found = grouped(rows, "ext_id", to_genre)
        return {ext_id: tuple(genres) for ext_id, genres in found.items()}

    async def set_for_item(self, item_id: int, genre_ids: list[int]) -> None:
        """Набор жанров заменяется целиком: пришедшее из источника — это весь
        список, а не добавка к прежнему."""
        cleared = clearing(item_genre_table, item_id)
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
        return await self._mapped(
            select(genre_table)
            .join(item_genre_table, item_genre_table.c.genre_id == genre_table.c.id)
            .where(item_genre_table.c.item_id == item_id)
            .order_by(genre_table.c.name),
            to_genre,
        )

    async def list_for_kind(self, kind: GenreKind) -> list[Genre]:
        """Наборов жанров два, и зовут их `film` и `game`, а не `movie` и
        `game`: `Kind.MOVIE`, переданный сюда по ошибке, вернёт пустой список,
        а не киношные жанры."""
        return await self._mapped(
            select(genre_table)
            .where(genre_table.c.kind == kind)
            .order_by(genre_table.c.name),
            to_genre,
        )
