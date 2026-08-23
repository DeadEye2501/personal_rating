"""Жанры в базе: свои, и правила из чужих меток, ведущие к ним."""

from sqlalchemy import Row, select
from sqlalchemy.dialects.sqlite import insert

from backend.model import Genre, GenreKind, GenreRule, GenreSource
from backend.storage.repository.base import Repository
from backend.storage.rows import grouped, to_genre
from backend.storage.statements import clearing
from backend.storage.tables import genre as genre_table
from backend.storage.tables import genre_rule as genre_rule_table
from backend.storage.tables import genre_rule_mark as mark_table
from backend.storage.tables import item_genre as item_genre_table


def _rule(marks: list[Row]) -> GenreRule:
    """Строки одного правила — со всеми его метками — в само правило."""
    head = marks[0]
    return GenreRule(
        genre=to_genre(head),
        required=frozenset(row.ext_id for row in marks if not row.forbidden),
        forbidden=frozenset(row.ext_id for row in marks if row.forbidden),
        alone=bool(head.alone),
    )


class GenresRepository(Repository):
    async def rules(self, source: GenreSource) -> tuple[GenreRule, ...]:
        """Правила одного источника целиком.

        Целиком, а не по метке: правило смотрит на весь набор меток игры сразу,
        и спрашивать его по одной метке нечем. Один запрос на источник — в
        выдаче поиска их два-три на все двадцать строк, а по кандидату это был
        бы запрос на кандидата."""
        rows = await self._rows(
            select(
                genre_rule_table.c.id.label("rule_id"),
                genre_rule_table.c.alone,
                genre_table.c.id,
                genre_table.c.name,
                genre_table.c.kind,
                mark_table.c.ext_id,
                mark_table.c.forbidden,
            )
            .join(genre_table, genre_table.c.id == genre_rule_table.c.genre_id)
            .join(mark_table, mark_table.c.rule_id == genre_rule_table.c.id)
            .where(genre_rule_table.c.source == source)
            .order_by(genre_table.c.name, genre_rule_table.c.id)
        )
        by_rule = grouped(rows, "rule_id", lambda row: row)
        return tuple(_rule(marks) for marks in by_rule.values())

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
        """Наборов жанров четыре, и киношный зовут `film`, а не `movie`:
        `Kind.MOVIE`, переданный сюда по ошибке, вернёт пустой список, а не
        киношные жанры."""
        return await self._mapped(
            select(genre_table)
            .where(genre_table.c.kind == kind)
            .order_by(genre_table.c.name),
            to_genre,
        )
