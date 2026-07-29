"""Список запланированного."""

from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.sqlite import insert

from backend.storage.repository.base import Repository
from backend.storage.tables import wishlist as wishlist_table


class WishlistRepository(Repository):
    async def add(self, item_id: int, now: datetime) -> None:
        # Повторное добавление не сдвигает дату: закладка ставится один раз.
        await self._run(
            insert(wishlist_table)
            .values(item_id=item_id, added_at=now)
            .on_conflict_do_nothing()
        )

    async def remove(self, item_id: int) -> None:
        await self._run(
            delete(wishlist_table).where(wishlist_table.c.item_id == item_id)
        )

    async def contains(self, item_id: int) -> bool:
        return await self._exists(
            select(wishlist_table.c.item_id)
            .where(wishlist_table.c.item_id == item_id)
        )

    async def list_ids(self, limit: int, offset: int) -> list[int]:
        """Новые сверху: порядок раздела «Хочу посмотреть» — по дате добавления
        от свежих к старым."""
        return await self._mapped(
            select(wishlist_table.c.item_id)
            .order_by(wishlist_table.c.added_at.desc(), wishlist_table.c.item_id)
            .limit(limit)
            .offset(offset),
            lambda row: row.item_id,
        )
