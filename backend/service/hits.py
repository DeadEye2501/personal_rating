"""Приведение того, что ответили источники, к тому виду, в котором это
показывают: находки — выдачей, отказы — плашкой.

Вынесено на втором потребителе: так собирает выдачу и поиск по строке, и поиск
по человеку. Разойдись эти две сборки — у одной из двух выдач пропали бы жанры
или бесплатная оценка источника, и заметить это было бы нечем: обе продолжали
бы отвечать успешно."""

from collections.abc import Callable, Iterable
from datetime import datetime

from backend.model import (
    CardView,
    Found,
    Genre,
    GenreSource,
    Outcome,
    Refusal,
    SearchHit,
    view_from_hit,
)
from backend.sources.convert import from_search
from backend.storage.repository.genres import GenresRepository
from backend.unique import unique, unique_by


def once(refusals: list[Refusal]) -> list[Refusal]:
    """Один отказ на источник и причину.

    Спросили пятерых найденных тёзок, лёг источник — плашка внизу всё равно
    говорит про источник, а он тут один. Тот же случай у строки поиска: обе её
    половины спрашивают один и тот же TMDB.

    Ключом, а не целиком: у сетевого отказа в `detail` стоит текст ошибки с
    адресом, и пять одинаковых по сути отказов вышли бы пятью разными."""
    return unique_by(refusals, lambda one: (one.source, one.reason))


def split(
    outcomes: Iterable[Outcome],
) -> tuple[list[list[SearchHit]], list[Refusal]]:
    """Найденное по источникам и отказы отдельно.

    `Missing` — не отказ, а пустая выдача: ни источника, ни причины у него нет,
    и в плашку он не годится. Инвариант один на оба поиска, и записан он тут:
    разойдись копии, в одной из двух выдач отказ терялся бы молча.

    Выдачи остаются по источникам, а не сливаются в одну: у игр их две, и
    переплести их можно только порознь."""
    answers: list[list[SearchHit]] = []
    refusals: list[Refusal] = []
    for outcome in outcomes:
        if isinstance(outcome, Refusal):
            refusals.append(outcome)
        elif isinstance(outcome, Found):
            answers.append(list(outcome.value))
    return answers, refusals


async def to_views(hits: list[SearchHit], genres: GenresRepository,
                   clock: Callable[[], datetime]) -> list[CardView]:
    """Справочник спрашивается по пространству, а не по кандидату: у страницы
    выдачи их два-три на все двадцать строк."""
    index: dict[GenreSource, dict[str, tuple[Genre, ...]]] = {}
    views = []
    for hit in hits:
        for space, _ in hit.genre_ext_ids:
            if space not in index:
                index[space] = await genres.index(space)
        views.append(view_from_hit(
            hit,
            _genres_of(hit, index),
            from_search(hit.source, hit.source_rating, clock()),
        ))
    return views


def _genres_of(
    hit: SearchHit,
    index: dict[GenreSource, dict[str, tuple[Genre, ...]]],
) -> tuple[Genre, ...]:
    """Незнакомое молча отбрасывается: заводить жанр на лету нельзя — имена в
    справочнике наши, а сборный жанр автоматически не разложить."""
    return tuple(unique(
        genre
        for space, ext_id in hit.genre_ext_ids
        for genre in index[space].get(ext_id, ())
    ))
