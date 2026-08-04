"""Моя оценка карточки."""

from datetime import datetime

from sqlalchemy import case, func, select
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
        # Строка хранит четыре вещи: балл, три шкалы и рецензию. Не осталось ни
        # одной — хранить нечего, и строка уходит: снаружи карточка с пустой
        # строкой и карточка без строки вовсе неразличимы, а «оценку сняли»
        # такая запись не значит — снятая оценка это её отсутствие.
        #
        # Условие смотрит на колонки после записи, а не на `values`: сюда ведут
        # три пути, и каждый пишет своё подмножество. Рецензия сравнивается
        # через `coalesce`: пустой её оставляет своя запись, пустотой —
        # заведение строки оценкой.
        emptied = clearing(rating_table, item_id).where(
            rating_table.c.score.is_(None),
            rating_table.c.visual.is_(None),
            rating_table.c.narrative.is_(None),
            rating_table.c.gameplay.is_(None),
            func.coalesce(rating_table.c.review, "") == "",
        )
        await self._run(
            statement.on_conflict_do_update(
                index_elements=[rating_table.c.item_id],
                set_={**values, "updated_at": now, "created_at": appeared},
            ),
            emptied,
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
