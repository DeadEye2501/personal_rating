"""Пачечное чтение карточек для показа."""

from collections import defaultdict
from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.model import CardView, view_from_item
from backend.storage.repository.base import Repository
from backend.storage.repository.entity import COMPANIES, PEOPLE, Entity
from backend.storage.rows import (
    to_tag,
    to_credit,
    to_external_id,
    to_external_rating,
    to_genre,
    to_item,
    to_rating,
)
from backend.storage.tables import (
    external_id,
    external_rating,
    genre,
    item,
    item_genre,
    item_tag,
    rating,
    tag,
    wishlist,
)


class ViewsRepository(Repository):
    """Собирает карточки для показа пачкой: по запросу на признак, а не на
    карточку. Порция ленты — 50 строк, и разница тут не косметическая."""

    async def views_for(self, item_ids: list[int]) -> dict[int, CardView]:
        if not item_ids:
            return {}
        async with self._sessions() as session:
            return await self._fetch_all(session, item_ids)

    async def in_order(self, item_ids: list[int]) -> list[CardView]:
        """Карточки в порядке спрошенных номеров: порядок принадлежит тому
        запросу, который их выбрал, а словарь его не хранит.

        Пропавшая между двумя запросами карточка тихо выпадает: удалить её
        человек мог ровно в этот промежуток, и ронять из-за неё всю выдачу
        незачем."""
        found = await self.views_for(item_ids)
        return [found[item_id] for item_id in item_ids if item_id in found]

    async def _fetch_all(
        self, session: AsyncSession, item_ids: list[int]
    ) -> dict[int, CardView]:
        views = {
            row.id: view_from_item(to_item(row))
            for row in (
                await session.execute(select(item).where(item.c.id.in_(item_ids)))
            ).all()
        }
        if not views:
            return {}

        known = list(views)
        genres = await self._genres(session, known)
        tags = await self._tags(session, known)
        cast = await self._credits(session, known, PEOPLE)
        studios = await self._credits(session, known, COMPANIES)
        external = await self._external(session, known)
        identifiers = await self._identifiers(session, known)
        ratings = await self._ratings(session, known)
        bookmarked = await self._wishlist(session, known)

        for item_id, view in views.items():
            views[item_id] = replace(
                view,
                genres=tuple(genres[item_id]),
                tags=tuple(tags[item_id]),
                people=tuple(cast[item_id]),
                companies=tuple(studios[item_id]),
                external=tuple(external[item_id]),
                external_ids=tuple(identifiers[item_id]),
                rating=ratings.get(item_id),
                in_wishlist=item_id in bookmarked,
            )
        return views

    async def _genres(self, session, item_ids):
        rows = await self._read(
            session,
            select(item_genre.c.item_id, genre)
            .join(genre, genre.c.id == item_genre.c.genre_id)
            .where(item_genre.c.item_id.in_(item_ids))
            .order_by(genre.c.name),
        )
        return self._by_card(rows, to_genre)

    async def _tags(self, session, item_ids):
        rows = await self._read(
            session,
            select(item_tag.c.item_id, tag.c.id, tag.c.name)
            .join(tag, tag.c.id == item_tag.c.tag_id)
            .where(item_tag.c.item_id.in_(item_ids))
            .order_by(tag.c.position),
        )
        return self._by_card(rows, to_tag)

    async def _credits(self, session, item_ids, entity: Entity):
        """Люди и студии читаются одним кодом: для приложения эти две сущности
        различаются только тем, что у людей есть порядок в титрах."""
        columns = [entity.credit.c.item_id, entity.table.c.name,
                   entity.credit.c.role, entity.table.c.source,
                   entity.table.c.source_id]
        if entity.position is not None:
            columns.append(entity.position)

        # У студий порядка в титрах нет, но устойчивый нужен и им: без него
        # они перетасовывались бы между показами одной и той же карточки.
        rows = await self._read(
            session,
            select(*columns)
            .join(entity.table, entity.table.c.id == entity.link)
            .where(entity.credit.c.item_id.in_(item_ids))
            .order_by(entity.position if entity.position is not None
                      else entity.table.c.id),
        )
        return self._by_card(rows, lambda row: to_credit(row, entity))

    async def _by_source(self, session, table, item_ids, make):
        """Всё содержимое таблицы чужих значений, разложенное по карточкам.

        Двое: чужие оценки и чужие идентификаторы. Остальные четыре `_*`-метода
        под это не подходят — `_genres` и `_tags` соединяют вторую таблицу,
        `_ratings` и `_wishlist` отдают не список.

        Сортировка тестом не сторожится, и не может: у обеих таблиц составной
        первичный ключ `(item_id, source)`, отбор по `item_id` идёт по нему же, и
        строки приходят упорядоченными по источнику сами. Замерено — снятый
        `order_by` не роняет ни одного теста. Держим потому, что порядок,
        доставшийся от выбора индекса, документацией SQLite не обещан."""
        rows = await self._read(
            session,
            select(table)
            .where(table.c.item_id.in_(item_ids))
            .order_by(table.c.source),
        )
        return self._by_card(rows, make)

    async def _external(self, session, item_ids):
        return await self._by_source(session, external_rating, item_ids,
                                     to_external_rating)

    async def _identifiers(self, session, item_ids):
        return await self._by_source(session, external_id, item_ids,
                                     to_external_id)

    async def _ratings(self, session, item_ids):
        rows = await self._read(
            session, select(rating).where(rating.c.item_id.in_(item_ids))
        )
        return {row.item_id: to_rating(row) for row in rows}

    async def _wishlist(self, session, item_ids):
        rows = await self._read(
            session,
            select(wishlist.c.item_id).where(wishlist.c.item_id.in_(item_ids)),
        )
        return {row.item_id for row in rows}

    async def _read(self, session, statement):
        """Одна сессия на все девять запросов: иначе каждый признак открывал бы
        свою, и «пачкой» осталось бы только на словах."""
        return (await session.execute(statement)).all()

    @staticmethod
    def _by_card(rows, make):
        """Строки, разложенные по карточкам. Ключ — `item_id` из самой строки:
        порядок он сохраняет, а карточку не путает."""
        found = defaultdict(list)
        for row in rows:
            found[row.item_id].append(make(row))
        return found
