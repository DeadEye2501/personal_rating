"""Приведение того, что ответили источники, к тому виду, в котором это
показывают: находки — выдачей, отказы — плашкой.

Сюда же отсев убранного человеком: это про ту же выдачу и того же потребителя.

Вынесено на втором потребителе: так собирает выдачу и поиск по строке, и поиск
по человеку. Разойдись эти две сборки — у одной из двух выдач пропали бы жанры,
бесплатная оценка источника или отсев убранного, и заметить это было бы нечем:
обе продолжали бы отвечать успешно."""

from collections.abc import Callable, Iterable
from datetime import datetime

from backend.model import (
    CardView,
    Found,
    Kind,
    Outcome,
    Refusal,
    SearchHit,
    Source,
    view_from_hit,
)
from backend.service.genres import book_for, genres_of
from backend.sources.convert import from_search
from backend.storage.repository.genres import GenresRepository
from backend.storage.repository.removed import RemovedRepository
from backend.unique import unique_by


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


def mark_of(hit: SearchHit) -> tuple[Kind, Source, str]:
    """Чем строка чужой выдачи опознаётся до всякой загрузки.

    Тип содержимого входит в тройку не для порядка: у TMDB фильмы и сериалы
    нумеруются порознь и сталкиваются числами — `tmdb/1399` это и фильм, и
    «Игра престолов»."""
    return (hit.kind, hit.source, hit.source_id)


async def without_removed(
    removed: RemovedRepository, answers: list[list[SearchHit]]
) -> list[list[SearchHit]]:
    """Выдачи без того, что человек уже убирал.

    Здесь, а не у каждой из двух сборок: внешнюю выдачу производят двое — строка
    поиска и клик по человеку, — и разойдись они, удалённое возвращалось бы одним
    жестом и не возвращалось другим. Ровно тот довод, ради которого этот модуль
    и заведён.

    Зовётся **до среза порции и до сборки карточек**: иначе убранная строка
    занимала бы слот из двадцати — а добрать двадцатую неоткуда, — и на неё
    уходил бы запрос за жанрами.

    Спрашивается один раз на все выдачи разом: запрос на каждую стоил бы
    столько же, сколько сам отсев экономит.

    Совпадение точное, по тройке. Ложных срабатываний тут не бывает по
    построению: названия не сравниваются вовсе, и одна игра в двух магазинах —
    две разные строки, из которых убрана может быть только названная."""
    gone = await removed.known(
        [mark_of(one) for answer in answers for one in answer])
    return [[one for one in answer if mark_of(one) not in gone]
            for answer in answers]


async def to_views(hits: list[SearchHit], genres: GenresRepository,
                   clock: Callable[[], datetime]) -> list[CardView]:
    """Справочник спрашивается по пространству, а не по кандидату: у страницы
    выдачи их два-три на все двадцать строк."""
    book = await book_for(genres, (
        space for hit in hits for space, _ in hit.genre_ext_ids
    ))
    return [
        view_from_hit(
            hit,
            genres_of(book, hit.genre_ext_ids),
            from_search(hit.source, hit.source_rating, clock()),
        )
        for hit in hits
    ]
