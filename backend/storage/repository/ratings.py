"""Моя оценка карточки."""

from datetime import datetime

from sqlalchemy import case, select
from sqlalchemy.dialects.sqlite import insert

from backend.model import Rating, average_score
from backend.storage.repository.base import Repository
from backend.storage.rows import to_rating
from backend.storage.statements import clearing
from backend.storage.tables import rating as rating_table


class RatingsRepository(Repository):
    async def _write(self, item_id: int, values: dict, now: datetime) -> None:
        statement = insert(rating_table).values(
            item_id=item_id, created_at=now, updated_at=now, **values
        )
        # `created_at` — когда карточка стала оценённой, а не когда завелась
        # строка: строку заводит и рецензия. Условие смотрит на колонки, а не на
        # `values`: оценка там своя у каждого пути и может не лежать вовсе.
        appeared = case(
            (rating_table.c.score.is_(None)
             & statement.excluded.score.is_not(None),
             statement.excluded.created_at),
            else_=rating_table.c.created_at,
        )
        await self._run(
            statement.on_conflict_do_update(
                index_elements=[rating_table.c.item_id],
                set_={**values, "updated_at": now, "created_at": appeared},
            )
        )

    async def set_score(self, item_id: int, score: float | None,
                        now: datetime) -> None:
        await self._write(item_id, {"score": score}, now)

    async def set_aspects(self, item_id: int, visual: int | None,
                          narrative: int | None, gameplay: int | None,
                          now: datetime) -> float | None:
        """Шкалы игры и пересчёт средней.

        Считает приложение, а не база: правило пересчёта зависит от
        `item.kind` — у фильма оценка выставленная, у игры средняя, — а
        `item.kind` в этой таблице нет."""
        score = average_score(visual, narrative, gameplay)
        await self._write(
            item_id,
            {"score": score, "visual": visual, "narrative": narrative,
             "gameplay": gameplay},
            now,
        )
        return score

    async def set_review(self, item_id: int, review: str, now: datetime) -> None:
        await self._write(item_id, {"review": review}, now)

    async def get(self, item_id: int) -> Rating | None:
        return await self._maybe(
            select(rating_table).where(rating_table.c.item_id == item_id),
            to_rating,
        )

    async def clear(self, item_id: int) -> None:
        """Снять оценку. Карточка остаётся — она уже загружена."""
        await self._run(clearing(rating_table, item_id))
