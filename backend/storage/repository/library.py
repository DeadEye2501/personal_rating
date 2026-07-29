"""Карточки библиотеки."""

from datetime import datetime

from sqlalchemy import Row, Select, delete, func, select, update

from backend.model import Item, Kind, Source, new_source_id
from backend.storage.posters import PosterStore
from backend.storage.repository.base import Repository
from backend.storage.session import fold
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


def _to_item(row: Row) -> Item:
    """Строка базы в тип границы слоёв.

    Пустой текст отдаётся пустой строкой, а не `None`: карточку правит и
    человек, и в его строке колонка бывает пустой — а в интерфейс `None`
    уехало бы словом «None»."""
    return Item(
        id=row.id,
        kind=Kind(row.kind),
        source=Source(row.source),
        source_id=row.source_id,
        title=row.title,
        synced_at=row.synced_at,
        original_title=row.original_title or "",
        year=row.year,
        released_at=row.released_at,
        synopsis=row.synopsis or "",
        poster_url=row.poster_url or "",
        runtime=row.runtime,
        seasons_count=row.seasons_count,
        episodes_count=row.episodes_count,
    )


class LibraryRepository(Repository):
    async def _one(self, statement: Select) -> Item | None:
        row = await self._row(statement)
        return _to_item(row) if row else None

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
            _to_item,
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
                (func.py_lower(item_table.c.title) == needle)
                | (func.py_lower(item_table.c.original_title) == needle),
            ),
            _to_item,
        )

    async def deletion_summary(self, item_id: int) -> dict[str, int | bool]:
        """Что именно пропадёт вместе с карточкой — для подтверждения."""
        tags = await self._row(
            select(func.count())
            .select_from(item_tag_table)
            .where(item_tag_table.c.item_id == item_id)
        )
        return {
            "has_rating": await self._exists(
                select(rating_table.c.item_id)
                .where(rating_table.c.item_id == item_id)
            ),
            "tags": tags.count,
            "in_wishlist": await self._exists(
                select(wishlist_table.c.item_id)
                .where(wishlist_table.c.item_id == item_id)
            ),
        }

    async def delete(self, item_id: int, posters: PosterStore) -> None:
        """Оценка, теги, закладка и связи уходят каскадом; постер — кодом:
        внешних ключей между двумя файлами SQLite не бывает."""
        await self._run(delete(item_table).where(item_table.c.id == item_id))
        await posters.delete(item_id)

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
