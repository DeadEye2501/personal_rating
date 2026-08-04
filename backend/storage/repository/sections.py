"""Вопросы к отфильтрованному набору раздела."""


from sqlalchemy import Column, Integer, Select, Table, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.model import (
    Bucket,
    Feed,
    Filters,
    Histogram,
    Kind,
    Section,
    Sort,
)
from backend.storage.repository.base import Repository
from backend.storage.session import folded
from backend.storage.tables import item, item_genre, item_tag, rating, wishlist

# Округление вниз делаем через CAST, а не через floor(): математические функции
# в SQLite включаются при сборке, и рассчитывать на них нельзя. Оценки
# положительные, для них CAST и есть округление вниз.
_COLUMN = cast(rating.c.score, Integer)

# Порядок по названию идёт по приведённой строке: встроенный в SQLite lower()
# умеет только ASCII, и «Аватар» с «аватаром» разъехались бы.
#
# Время оценки — `created_at`, когда её поставили: соседний `updated_at` уезжал
# бы и от смены балла, и от рецензии, и от каждой шкалы игры.
_KEYS = {
    Sort.SCORE: rating.c.score,
    Sort.RATED_AT: rating.c.created_at,
    Sort.YEAR: item.c.year,
    Sort.TITLE: folded(item.c.title),
    Sort.ADDED_AT: wishlist.c.added_at,
}

# Чем раздел разбивает ничью основного критерия. Пустых значений тут не бывает:
# `_narrow` уже оставил в «Оценённых» только оценённое, а в отложенном — только
# отложенное.
_SECONDARY = {
    Section.RATED: rating.c.created_at,
    Section.WISHLIST: wishlist.c.added_at,
}


def _carrying(link: Table, key: Column, ids: tuple[int, ...]) -> Select:
    """Номера карточек, у которых есть хоть одна из этих меток или жанров.

    Годится исключению, а не включению: «нет ни одной из этих» — это и есть
    отрицание «есть хоть одна»."""
    return select(link.c.item_id).where(key.in_(ids))


def _carrying_all(link: Table, key: Column, ids: tuple[int, ...]) -> Select:
    """Номера карточек, у которых есть **все** эти метки или жанры.

    Решение пользователя 02.08.2026: каждая добавленная метка сужает набор.
    Раньше внутри признака стояло «или», и вторая метка приводила карточки,
    которых с первой не было, — то есть отбор расширялся отбором.

    От повтора в самом отборе — одна и та же метка выбрана дважды — защищает
    `set(ids)`, а не `distinct`: `IN (5, 5)` счёт не поднимает. `distinct` стоит
    ради второго: он делает счёт независимым от того, сторожит ли уникальность
    пары сама таблица связи."""
    return (
        _carrying(link, key, ids)
        .group_by(link.c.item_id)
        .having(func.count(func.distinct(key)) == len(set(ids)))
    )


def _included(query: Select, filters: Filters) -> Select:
    """«И» и между признаками, и внутри признака: каждый выбранный добавляет
    своё условие к остальным.

    Оценка — исключение, и не по решению, а по устройству: она у карточки одна,
    и «семь и восемь разом» не бывает ни у чего. Там выбранные столбцы
    складываются по «или», как в гистограмме."""
    if filters.tag_ids:
        query = query.where(item.c.id.in_(
            _carrying_all(item_tag, item_tag.c.tag_id, filters.tag_ids)
        ))
    if filters.genre_ids:
        query = query.where(item.c.id.in_(
            _carrying_all(item_genre, item_genre.c.genre_id, filters.genre_ids)
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
    """Два ответа про один и тот же набор: кто в него попал и как в нём
    распределены оценки. Оба стоят на общем `_narrow`, иначе гистограмма
    показывала бы не то, что видно в ленте.

    Карточки отдаются номерами: состав собирает `ViewsRepository`, а спрошенный
    тем же запросом дал бы строку на каждый жанр и тег.

    Число ступеней обязательно и приходит из настроек: у гистограммы столько
    столбцов, сколько их в шкале."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession],
                 scale: int) -> None:
        super().__init__(sessions)
        self._scale = scale

    async def ids(self, feed: Feed, limit: int, offset: int) -> list[int]:
        key = _KEYS[feed.order.key]
        # Ничью разбивает дата раздела, и всегда свежим вверх: сторона у неё
        # своя, а не изнанка выбранного критерия. Третий ключ — номер: без него
        # равные даты перетасовывались бы между порциями, и карточка попадала бы
        # в две сразу либо ни в одну.
        query = (
            self._narrow(select(item.c.id), feed.section, feed.kind, feed.filters)
            .order_by(key.desc() if feed.order.descending else key.asc(),
                      _SECONDARY[feed.section].desc(),
                      item.c.id)
            .limit(limit)
            .offset(offset)
        )
        return [row.id for row in await self._rows(query)]

    async def histogram(self, kind: Kind, filters: Filters) -> Histogram:
        """Столбец на каждую ступень шкалы, включая пустые: пустой столбец — это
        сведение, а не отсутствие данных. Плюс подвал: сколько всего и средняя.

        Раздел здесь всегда «Оценённые»: гистограмма строится по выставленным
        оценкам, и в «Хочу посмотреть» считать нечего.

        Фильтры действуют целиком, включая фильтр по оценке: гистограмма
        показывает тот же набор, что и список карточек, и ничем от него не
        отличается. То, что отбор по оценке оставляет от неё выбранные столбцы,
        и есть ответ. Решено пользователем 01.08.2026."""
        counted = self._narrow(
            select(_COLUMN.label("bucket"), func.count().label("total")),
            Section.RATED, kind, filters,
        ).group_by("bucket")
        # Средняя считается по неокруглённым оценкам: у игр score — среднее трёх
        # шкал, и сумма по столбцам занизила бы её почти на полбалла. Всего же
        # считать вторым запросом нечего: это сумма столбцов.
        mean = self._narrow(
            select(func.avg(rating.c.score).label("mean")),
            Section.RATED, kind, filters,
        )

        steps = range(1, self._scale + 1)
        counts = dict.fromkeys(steps, 0)
        for row in await self._rows(counted):
            counts[row.bucket] = row.total
        average = (await self._row(mean)).mean

        return Histogram(
            buckets=tuple(Bucket(score=score, count=counts[score])
                          for score in steps),
            total=sum(counts.values()),
            average=average,
        )

    def _narrow(self, query: Select, section: Section, kind: Kind,
                filters: Filters) -> Select:
        """Общая часть запроса раздела и гистограммы: они обязаны считать по
        одному и тому же набору, иначе отфильтрованную гистограмму не увидеть."""
        query = query.select_from(
            item
            .outerjoin(rating, rating.c.item_id == item.c.id)
            .outerjoin(wishlist, wishlist.c.item_id == item.c.id)
        ).where(item.c.kind == kind)

        if section is Section.RATED:
            query = query.where(rating.c.score.is_not(None))
        elif section is Section.WISHLIST:
            query = query.where(wishlist.c.item_id.is_not(None))

        return _excluded(_included(query, filters), filters)
