"""Что человек убрал из выдачи насовсем."""

from itertools import batched

from sqlalchemy import delete, select, tuple_
from sqlalchemy.dialects.sqlite import insert

from backend.model import CardView, Item, Kind, Source
from backend.storage.repository.base import Repository
from backend.storage.tables import removed as removed_table

# По сколько строк спрашивать за раз. Тройка кладёт по три подставляемых
# значения на строку, а у SQLite их число ограничено: старый предел — 999, и
# триста строк укладываются в него с запасом даже там.
BATCH = 300


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

    async def listing(self, kind: Kind) -> list[CardView]:
        """Что человек убирал в этой вкладке. Вкладка — первичный фильтр везде,
        и здесь тоже.

        `CardView`, а не свой тип: строка рисуется свёрнутой карточкой, и
        показывать в ней, кроме названия, нечего — остальные поля пустуют ровно
        так же, как у кандидата выдачи. Заводить ради четырёх колонок второй тип
        границы значит вести его и через мост, и через сторожа поверхности.

        Порядок по названию: своего времени у строки нет, таблица его не хранит,
        а без порядка список прыгал бы между перерисовками."""
        rows = await self._rows(
            select(removed_table)
            .where(removed_table.c.kind == kind)
            .order_by(removed_table.c.title)
        )
        return [CardView(kind=Kind(row.kind), source=Source(row.source),
                         source_id=row.source_id, title=row.title)
                for row in rows]

    async def forget(self, kind: Kind, source: Source, source_id: str) -> None:
        """Снять пометку. Возвращается не карточка, а только память о ней: игра
        снова находится поиском, завести её можно заново — уже как новую, без
        прежней оценки.

        Пометки может не оказаться вовсе, и это исход, а не отказ: человек нажал
        дважды, страница дважды позвала мост."""
        await self._run(
            delete(removed_table).where(
                removed_table.c.kind == kind,
                removed_table.c.source == source,
                removed_table.c.source_id == source_id,
            )
        )

    async def known(
        self, marks: list[tuple[Kind, Source, str]]
    ) -> set[tuple[str, str, str]]:
        """Какие из спрошенных строк человек уже убирал.

        Спрашивается набором, а не по строке: у выдачи их два-три десятка, и
        запрос на кандидата стоил бы столько же, сколько сама выдача.

        Тройкой, а не парой: у TMDB фильмы и сериалы нумеруются порознь и
        сталкиваются числами, и без типа содержимого удалённый фильм молча унёс
        бы одноимённый по номеру сериал.

        Пачками, а не одним запросом: «два-три десятка» верно для строки поиска,
        а клик по имени в музыке приводит до двадцати пяти исполнителей, у
        каждого до тысячи альбомов. У SQLite есть предел на число подставляемых
        значений, тройка кладёт по три на строку, и за пределом падает **весь**
        запрос — поиск отвечает непредвиденным сбоем."""
        found: set[tuple[str, str, str]] = set()
        for part in batched(marks, BATCH):
            rows = await self._rows(
                select(removed_table.c.kind, removed_table.c.source,
                       removed_table.c.source_id)
                .where(tuple_(removed_table.c.kind, removed_table.c.source,
                              removed_table.c.source_id).in_(part))
            )
            found |= {(row.kind, row.source, row.source_id) for row in rows}
        return found
