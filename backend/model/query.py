"""Язык, которым лента разговаривает с базой о разделах."""

from dataclasses import dataclass
from enum import StrEnum

from backend.model.kinds import Kind


class Section(StrEnum):
    """Разделы, которые спрашивают у базы. Поиска тут нет: он спрашивает у
    источников, и фильтры на него не действуют."""

    RATED = "rated"
    WISHLIST = "wishlist"


class Sort(StrEnum):
    """Критерии порядка. Четыре первых перебирает кнопка в шапке, каждый в две
    стороны; ADDED_AT в переборе не участвует — это порядок по умолчанию в
    «Хочу посмотреть»."""

    SCORE = "score"          # своя оценка
    RATED_AT = "rated_at"    # когда оценивал
    YEAR = "year"            # год выхода
    TITLE = "title"          # по алфавиту
    ADDED_AT = "added_at"    # когда отложил


@dataclass(frozen=True, slots=True)
class Order:
    """Критерий и сторона. Умолчание — сверху то, чего больше: высокие оценки,
    свежие даты, новые фильмы."""

    key: Sort
    descending: bool = True


@dataclass(frozen=True, slots=True)
class Filters:
    """Пустой набор — это «показать всё».

    Внутри одного признака включённые складываются по «или», между признаками —
    по «и». Исключённые вычитаются последними и сильнее включённых: выбрал
    драму, исключил ужасы — получил драмы, среди которых нет ни одного ужаса,
    даже если он заодно и драма."""

    tag_ids: tuple[int, ...] = ()
    genre_ids: tuple[int, ...] = ()
    scores: tuple[int, ...] = ()   # столбцы гистограммы, дробные округляются вниз

    excluded_tag_ids: tuple[int, ...] = ()
    excluded_genre_ids: tuple[int, ...] = ()
    excluded_scores: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class Feed:
    """О чём спрашивает лента: раздел, тип содержимого, фильтры и порядок.

    Четыре вещи ходят вместе всегда: раздел без типа содержимого — это половина
    вопроса, а фильтры и порядок держит та же шапка, что и переключатель
    раздела."""

    section: Section
    kind: Kind
    filters: Filters
    order: Order


@dataclass(frozen=True, slots=True)
class Bucket:
    """Столбец гистограммы."""

    score: int
    count: int


@dataclass(frozen=True, slots=True)
class Histogram:
    """Столбцы и подвал под ними.

    `average` считает база по неокруглённым оценкам, а не клиент по столбцам:
    у игр оценка — среднее трёх шкал, и сумма по округлённым вниз столбцам
    занижала бы результат почти на полбалла."""

    buckets: tuple[Bucket, ...]
    total: int
    average: float | None   # пусто — считать нечего
