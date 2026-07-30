"""Карточки библиотеки."""

from datetime import datetime

from sqlalchemy import Select, delete, func, select, update

from backend.model import Item, Kind, Source, new_source_id
from backend.storage.posters import PosterStore
from backend.storage.repository.base import Repository
from backend.storage.rows import to_item
from backend.storage.session import fold, folded
from backend.storage.tables import item as item_table
from backend.storage.tables import item_tag as item_tag_table
from backend.storage.tables import rating as rating_table
from backend.storage.tables import wishlist as wishlist_table


class ItemExists(Exception):
    """Пара (source, source_id) уже занята другой карточкой."""


_FIELDS = (
    "kind", "source", "source_id", "title", "original_title", "year",
    "released_at", "synopsis", "poster_url", "runtime", "seasons_count",
    "episodes_count", "synced_at",
)


def _values(item: Item) -> dict:
    """Карточка в вид для вставки. `id` не берётся: его выдаёт база.

    Перечисления не переводятся в строку по пути: они `StrEnum`, то есть уже
    строки, и в колонку ложатся своим значением."""
    return {name: getattr(item, name) for name in _FIELDS}


class LibraryRepository(Repository):
    async def _one(self, statement: Select) -> Item | None:
        return await self._maybe(statement, to_item)

    async def create(self, item: Item) -> int:
        return await self._created(
            item_table.insert().values(**_values(item)).returning(item_table.c.id),
            ItemExists(f"{item.source}:{item.source_id} уже в библиотеке"),
        )

    async def get(self, item_id: int) -> Item | None:
        return await self._one(select(item_table).where(item_table.c.id == item_id))

    async def find_by_source(self, source: Source, source_id: str) -> Item | None:
        return await self._one(
            select(item_table).where(
                item_table.c.source == source,
                item_table.c.source_id == source_id,
            )
        )

    async def list_by_kind(self, kind: Kind, limit: int, offset: int) -> list[Item]:
        """Порядок по названию — решение этого плана, а не спеки: у разделов
        свои порядки, и они лягут в запросы сервисного слоя. Здесь нужен
        любой устойчивый, чтобы порции не перемешивались между запросами."""
        return await self._mapped(
            select(item_table)
            .where(item_table.c.kind == kind)
            .order_by(item_table.c.title, item_table.c.id)
            .limit(limit)
            .offset(offset),
            to_item,
        )

    async def find_by_title(self, kind: Kind, title: str) -> list[Item]:
        """Для предупреждения о совпадении: сравнение по обоим названиям и
        только внутри своего типа содержимого.

        Обе стороны приводятся одной и той же функцией: встроенный в SQLite
        lower() умеет только ASCII, и с ним русские названия не совпали бы
        никогда."""
        needle = fold(title.strip())
        return await self._mapped(
            select(item_table).where(
                item_table.c.kind == kind,
                (folded(item_table.c.title) == needle)
                | (folded(item_table.c.original_title) == needle),
            ),
            to_item,
        )

    async def search(self, kind: Kind, query: str, limit: int) -> list[int]:
        """Поиск по своей библиотеке: вхождение в любое из двух названий.

        В отличие от `find_by_title`, который сравнивает названия целиком ради
        предупреждения о совпадении, здесь нужна подстрока. `autoescape` гасит
        `%` и `_` в самом запросе: иначе «%» вывалил бы всю библиотеку."""
        needle = fold(query.strip())
        if not needle:
            return []

        rows = await self._rows(
            select(item_table.c.id)
            .where(
                item_table.c.kind == kind,
                folded(item_table.c.title).contains(needle, autoescape=True)
                | folded(item_table.c.original_title).contains(
                    needle, autoescape=True
                ),
            )
            .order_by(item_table.c.title)
            .limit(limit)
        )
        return [row.id for row in rows]

    async def deletion_summary(self, item_id: int) -> dict[str, int | bool]:
        """Что именно пропадёт вместе с карточкой — для подтверждения."""
        tags = await self._row(
            select(func.count())
            .select_from(item_tag_table)
            .where(item_tag_table.c.item_id == item_id)
        )
        return {
            "has_rating": await self._has_item(rating_table, item_id),
            "tags": tags.count,
            "in_wishlist": await self._has_item(wishlist_table, item_id),
        }

    async def delete(self, item_id: int, posters: PosterStore) -> None:
        """Оценка, теги, закладка и связи уходят каскадом; постер — кодом:
        внешних ключей между двумя файлами SQLite не бывает.

        Постер уходит первым, и порядок здесь не косметика. Оборвись удаление на
        середине — у обратного порядка в хранилище остался бы постер без хозяина,
        а `id` карточки SQLite выдаёт повторно: `item` заведён без
        `AUTOINCREMENT`, и следующая карточка молча получила бы чужую обложку.
        В этом порядке остаётся карточка без обложки, а её скачают заново по
        `poster_url` при первом же показе."""
        await posters.delete(item_id)
        await self._run(delete(item_table).where(item_table.c.id == item_id))

    async def refresh_series_counts(self, item_id: int,
                                    seasons_count: int | None,
                                    episodes_count: int | None,
                                    now: datetime) -> None:
        """Единственное, что обновляется автоматически. Параметров, которыми
        можно затронуть название или синопсис, здесь нет намеренно: они
        принадлежат человеку с момента создания."""
        await self._run(
            update(item_table)
            .where(item_table.c.id == item_id)
            .values(seasons_count=seasons_count,
                    episodes_count=episodes_count,
                    synced_at=now)
        )

    async def replace_fields(self, item_id: int, item: Item) -> None:
        """Правка человеком: пишет все поля карточки. Источник и его
        идентификатор не трогает — это привязка, отдельная операция."""
        values = _values(item)
        del values["source"], values["source_id"]
        await self._run(
            update(item_table).where(item_table.c.id == item_id).values(**values)
        )

    async def link(self, item_id: int, source: Source, source_id: str,
                   now: datetime) -> None:
        """Привязка — правка двух полей. Оценка, теги и закладка держатся за
        `item.id`, а он не меняется.

        `synced_at` ставится заново: иначе карточка, заведённая полгода назад,
        сразу окажется просроченной и уедет на перезапрос, которому нечего
        запрашивать. Время приходит параметром, как во всех записях проекта:
        читай его функция сама, проверить записанное было бы нечем."""
        await self._written(
            update(item_table)
            .where(item_table.c.id == item_id)
            .values(source=source, source_id=source_id, synced_at=now),
            ItemExists(f"{source}:{source_id} уже в библиотеке"),
        )

    async def unlink(self, item_id: int) -> None:
        """Источник снимается, карточка становится ручной. Данные остаются:
        они уже твои."""
        await self._run(
            update(item_table)
            .where(item_table.c.id == item_id)
            .values(source=Source.MANUAL, source_id=new_source_id())
        )
