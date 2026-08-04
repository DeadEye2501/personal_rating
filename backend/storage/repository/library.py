"""Карточки библиотеки."""

from datetime import datetime

from sqlalchemy import Select, delete, exists, func, select, update

from backend.model import Item, ItemExists, Kind, Source, new_source_id
from backend.storage.entity import COMPANIES, PEOPLE, Entity
from backend.storage.repository.base import Repository
from backend.storage.rows import to_item
from backend.storage.session import fold, folded
from backend.storage.tables import item as item_table
from backend.storage.tables import item_tag as item_tag_table
from backend.storage.tables import rating as rating_table
from backend.storage.tables import wishlist as wishlist_table


_FIELDS = (
    "kind", "source", "source_id", "title", "original_title", "year",
    "released_at", "synopsis", "poster_url", "runtime", "seasons_count",
    "episodes_count", "synced_at",
)


def _named(entity: Entity, needle: str):
    """Связан ли с карточкой кто-то с таким именем.

    Вынесено, потому что людей и студий две штуки, а запрос у них один и тот же
    с точностью до описателя. Отбор по `item_id` внутри обязателен: без него
    нашлась бы любая карточка, пока в базе есть хоть один человек с таким
    именем."""
    return exists(
        select(entity.credit.c.item_id)
        .join_from(entity.credit, entity.table, entity.link == entity.table.c.id)
        .where(entity.credit.c.item_id == item_table.c.id,
               folded(entity.table.c.name).contains(needle, autoescape=True))
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

    async def find_by_source(self, kind: Kind, source: Source,
                             source_id: str) -> Item | None:
        """Тройкой, а не парой: тем же ключом карточка опознаётся уникальной.
        Номер `550` у TMDB носят и фильм, и сериал."""
        return await self._one(
            select(item_table).where(
                item_table.c.kind == kind,
                item_table.c.source == source,
                item_table.c.source_id == source_id,
            )
        )

    async def list_by_kind(self, kind: Kind, limit: int, offset: int) -> list[Item]:
        """Порядок по названию — решение этого плана, а не спеки: у разделов
        свои порядки, и они лягут в запросы сервисного слоя. Здесь нужен
        любой устойчивый, чтобы порции не перемешивались между запросами.

        Второй ключ — страховка, и тестом она не сторожится: одинаковые названия
        проект разрешает прямо, но ничью SQLite и без ключа раскладывает по
        rowid, то есть ровно так же. Замерено — снятый `id` не роняет ни одного
        теста. Держим потому, что порядок ничьей документацией SQLite не
        обещан."""
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
        """Широкий общий поиск: по людям и студиям, по названию и по
        оригинальному. Ветка студий для игровой половины библиотеки —
        единственная работающая: людей у игр не бывает.

        В отличие от `find_by_title`, который сравнивает названия целиком ради
        предупреждения о совпадении, здесь нужна подстрока. `autoescape` гасит
        `%` и `_` в самом запросе: иначе «%» вывалил бы всю библиотеку.

        Это про строку поиска, а не про клик по имени: тот ищет по строке
        человека в базе и сюда не заходит вовсе.

        `distinct` тут не нужен, и это замерено: состав подмешан предикатом
        `EXISTS`, а он строк не размножает — человек с двумя ролями даёт одну
        карточку и без него. Стоял он с тех пор, когда запрос задумывался
        соединением, и снят. Сегодняшнюю реализацию этим свойством никто не
        проверяет: наблюдать нечего. Тест на две роли держим описанием свойства —
        покраснеет он, если запрос вернут к соединению."""
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
                )
                | _named(PEOPLE, needle)
                | _named(COMPANIES, needle),
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
        # Оценка и рецензия лежат в одной строке, и наличием строки их не
        # различить: рецензия заводит её сама, со `score = NULL`. Спрошенные
        # порознь, они и в вопросе называются порознь — иначе карточке с одной
        # рецензией окно обещало бы потерю оценки, которой нет, и молчало бы о
        # том, что пропадёт на самом деле.
        mine = await self._row(
            select(rating_table.c.score, rating_table.c.review)
            .where(rating_table.c.item_id == item_id)
        )
        return {
            "has_rating": mine is not None and mine.score is not None,
            "has_review": bool(mine is not None and mine.review),
            "tags": tags.count,
            "in_wishlist": await self._has_item(wishlist_table, item_id),
        }

    async def delete(self, item_id: int) -> None:
        """Оценка, теги, закладка и связи уходят каскадом. Обложка лежит во втором
        файле базы, внешних ключей между файлами не бывает, и убирает её
        `service/removal.py` — он же задаёт порядок двух удалений."""
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
        """Правка человеком: пишет все поля карточки.

        Три поля не трогает. Источник и его идентификатор — это привязка,
        отдельная операция. `synced_at` — отметка о разговоре с источником, а
        правка руками разговором не является: поставь её здесь, и карточка
        объявит себя только что обновлённой, а дешёвый перезапрос сезонов не
        случится ещё месяц."""
        values = _values(item)
        del values["source"], values["source_id"], values["synced_at"]
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
