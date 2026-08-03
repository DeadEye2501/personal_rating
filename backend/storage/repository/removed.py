"""Что человек убрал из выдачи насовсем."""

from sqlalchemy import select, tuple_
from sqlalchemy.dialects.sqlite import insert

from backend.model import Item, Kind, Source
from backend.storage.repository.base import Repository
from backend.storage.tables import removed as removed_table


class RemovedRepository(Repository):
    """Отдельным репозиторием, а не методом библиотеки: `item` эта таблица не
    касается вовсе — карточки к моменту записи уже нет, и ссылаться не на что.
    Её предмет — строка чужой выдачи, а не своя карточка."""

    async def remember(self, item: Item) -> None:
        """Ручная карточка не пишется: её `source_id` выдуман при создании, из
        выдачи она не приходит никогда, и запись отсеяла бы ровно ничего.

        Повтор молчит: удалить одну и ту же игру дважды человек вправе — он
        завёл её заново, посмотрел и убрал опять."""
        if item.source is Source.MANUAL:
            return
        await self._run(
            insert(removed_table)
            .values(kind=item.kind, source=item.source,
                    source_id=item.source_id, title=item.title)
            .on_conflict_do_nothing()
        )

    async def known(
        self, marks: list[tuple[Kind, Source, str]]
    ) -> set[tuple[str, str, str]]:
        """Какие из спрошенных строк человек уже убирал.

        Спрашивается набором, а не по строке: у выдачи их два-три десятка, и
        запрос на кандидата стоил бы столько же, сколько сама выдача.

        Тройкой, а не парой: у TMDB фильмы и сериалы нумеруются порознь и
        сталкиваются числами, и без типа содержимого удалённый фильм молча унёс
        бы одноимённый по номеру сериал."""
        if not marks:
            return set()
        rows = await self._rows(
            select(removed_table.c.kind, removed_table.c.source,
                   removed_table.c.source_id)
            .where(tuple_(removed_table.c.kind, removed_table.c.source,
                          removed_table.c.source_id).in_(marks))
        )
        return {(row.kind, row.source, row.source_id) for row in rows}
