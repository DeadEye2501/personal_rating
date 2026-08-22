"""Список треков альбома."""

from sqlalchemy import insert, select

from backend.storage.repository.base import Repository
from backend.storage.statements import clearing
from backend.storage.tables import track


class TracksRepository(Repository):
    async def replace(self, item_id: int, titles: list[str]) -> None:
        """Набор целиком, а не долив: убранный человеком трек обязан исчезнуть,
        иначе убрать его нечем. Порядок задаёт сам список — он и есть то, что
        человек набрал.

        Пустой список означает «треков нет»: старые уходят, новых не приходит,
        и вставки не случается вовсе."""
        await self._run(clearing(track, item_id))
        if titles:
            await self._run(insert(track).values([
                {"item_id": item_id, "position": at, "title": title}
                for at, title in enumerate(titles)
            ]))

    async def of(self, item_id: int) -> list[str]:
        """Порядок берётся из `position`, а не из порядка строк: rowid ничего
        не обещает."""
        return await self._mapped(
            select(track.c.title)
            .where(track.c.item_id == item_id)
            .order_by(track.c.position),
            lambda row: row.title,
        )
