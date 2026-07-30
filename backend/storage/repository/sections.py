"""Кто попадает в ленту и в каком порядке."""

from sqlalchemy import Column, Integer, Select, Table, cast, select

from backend.model import Feed, Filters, Section, Sort
from backend.storage.repository.base import Repository
from backend.storage.session import folded
from backend.storage.tables import item, item_genre, item_tag, rating, wishlist

# Округление вниз делаем через CAST, а не через floor(): математические функции
# в SQLite включаются при сборке, и рассчитывать на них нельзя. Оценки
# положительные, для них CAST и есть округление вниз.
_COLUMN = cast(rating.c.score, Integer)

# Порядок по названию идёт по приведённой строке: встроенный в SQLite lower()
# умеет только ASCII, и «Аватар» с «аватаром» разъехались бы.
_KEYS = {
    Sort.SCORE: rating.c.score,
    Sort.RATED_AT: rating.c.updated_at,
    Sort.YEAR: item.c.year,
    Sort.TITLE: folded(item.c.title),
    Sort.ADDED_AT: wishlist.c.added_at,
}


def _carrying(link: Table, key: Column, ids: tuple[int, ...]) -> Select:
    """Номера карточек, у которых есть хоть одна из этих метк или жанров.
    Внутри признака отобранное складывается по «или» — это и есть `in_`."""
    return select(link.c.item_id).where(key.in_(ids))


def _included(query: Select, filters: Filters) -> Select:
    """Между признаками «и»: каждый добавляет своё условие к остальным."""
    if filters.tag_ids:
        query = query.where(item.c.id.in_(
            _carrying(item_tag, item_tag.c.tag_id, filters.tag_ids)
        ))
    if filters.genre_ids:
        query = query.where(item.c.id.in_(
            _carrying(item_genre, item_genre.c.genre_id, filters.genre_ids)
        ))
    if filters.scores:
        query = query.where(_COLUMN.in_(filters.scores))
    return query


def _excluded(query: Select, filters: Filters) -> Select:
    """Исключённое сильнее включённого, и держится это не порядком условий, а их
    видом: включённое добавляет «есть среди этих», исключённое — «нет среди
    тех», и в конъюнкции второе не отменить первым. Выбрал драму, исключил
    ужасы — ужас, который заодно и драма, не покажется."""
    if filters.excluded_tag_ids:
        query = query.where(item.c.id.not_in(
            _carrying(item_tag, item_tag.c.tag_id, filters.excluded_tag_ids)
        ))
    if filters.excluded_genre_ids:
        query = query.where(item.c.id.not_in(
            _carrying(item_genre, item_genre.c.genre_id,
                      filters.excluded_genre_ids)
        ))
    if filters.excluded_scores:
        # NULL здесь обязателен. В разделе «Хочу посмотреть» у отложенного, но
        # не оценённого, score пуст, а `NULL NOT IN (3)` в SQL — это NULL, а не
        # истина: строка отсеется, и карточки молча пропадут из раздела.
        # Неоценённое исключением по оценке не задевается.
        query = query.where(
            _COLUMN.is_(None) | _COLUMN.not_in(filters.excluded_scores)
        )
    return query


class SectionsRepository(Repository):
    """Отдаёт идентификаторы: состав карточки собирает `ViewsRepository`, и
    спрошенный тем же запросом дал бы строку на каждый жанр и тег."""

    async def ids(self, feed: Feed, limit: int, offset: int) -> list[int]:
        key = _KEYS[feed.order.key]
        # Второй ключ — идентификатор: без него равные оценки перетасовывались
        # бы между порциями, и карточка попадала бы в две сразу либо ни в одну.
        query = (
            self._narrow(select(item.c.id), feed)
            .order_by(key.desc() if feed.order.descending else key.asc(),
                      item.c.id)
            .limit(limit)
            .offset(offset)
        )
        return [row.id for row in await self._rows(query)]

    def _narrow(self, query: Select, feed: Feed) -> Select:
        """Общая часть запроса раздела и гистограммы: они обязаны считать по
        одному и тому же набору, иначе отфильтрованную гистограмму не увидеть."""
        query = query.select_from(
            item
            .outerjoin(rating, rating.c.item_id == item.c.id)
            .outerjoin(wishlist, wishlist.c.item_id == item.c.id)
        ).where(item.c.kind == feed.kind)

        if feed.section is Section.RATED:
            query = query.where(rating.c.score.is_not(None))
        elif feed.section is Section.WISHLIST:
            query = query.where(wishlist.c.item_id.is_not(None))

        return _excluded(_included(query, feed.filters), feed.filters)
