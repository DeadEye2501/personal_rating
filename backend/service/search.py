"""Что найдётся по запросу."""

import asyncio
from collections.abc import Callable
from datetime import datetime

from backend.model import (
    CardView,
    ExternalSearch,
    Kind,
    SearchHit,
)
from backend.service.asking import answered_all
from backend.service.filmography import Filmographies
from backend.service.hits import once, split, to_views
from backend.sources.registry import Sources
from backend.storage.repository.genres import GenresRepository
from backend.storage.repository.library import LibraryRepository
from backend.storage.repository.views import ViewsRepository
from backend.unique import unique_by

# Ровно страница выдачи TMDB: одна порция стоит одного запроса. Величина —
# настройка, а не свойство схемы.
SEARCH_SIZE = 20


def _weave(answers: list[list[SearchHit]]) -> list[SearchHit]:
    """Несколько выдач — вперемешку, по одному кандидату по кругу.

    Выдач бывает две по двум разным причинам. У игр это два магазина, и склеить
    их подряд нельзя: поиск GOG никогда не отвечает «не найдено» и на
    бессмыслицу отдаёт два десятка несвязанных игр — подряд это значит, что
    вторая половина страницы всегда мусор GOG, а настоящие его находки
    начинаются там, куда никто не доскроллит. У кино источник один, но половины
    у строки две — названия и работы найденных людей, — и подряд фильмография
    одного актёра вытеснила бы за экран всё найденное по названию.

    Порядок внутри каждой выдачи сохраняется: он задан источником."""
    woven = []
    for position in range(max((len(answer) for answer in answers), default=0)):
        for answer in answers:
            if position < len(answer):
                woven.append(answer[position])
    return woven


class SearchService:
    """Поиск идёт сразу по двум местам, и метод у каждого свой: своё отдаётся
    первым и работает без сети, внешнее доливается по готовности."""

    def __init__(self, library: LibraryRepository, views: ViewsRepository,
                 sources: Sources, genres: GenresRepository,
                 clock: Callable[[], datetime] = datetime.now) -> None:
        self._library = library
        self._views = views
        self._sources = sources
        self._works = Filmographies(sources)
        self._genres = genres
        # Часы внедряются, как во всех записях проекта: отметка бесплатной оценки
        # кандидата в базу не попадает, но брать время изнутри — путь к тому, что
        # однажды попадёт и проверить это будет нечем.
        self._clock = clock

    async def local(self, kind: Kind, query: str) -> list[CardView]:
        item_ids = await self._library.search(kind, query, limit=SEARCH_SIZE)
        return await self._views.in_order(item_ids)

    async def external(self, kind: Kind, query: str) -> ExternalSearch:
        """Строка ищет и по названию, и по имени человека — всегда, а не «если
        названием ничего не нашлось»: решение пользователя 01.08.2026.

        Обе половины уходят разом: сроки ожидания у них свои, и спроси их по
        очереди — выдача ждала бы их сумму. У игр в первой половине два
        магазина, и отказ одного не скрывает ответ другого."""
        outcomes, (works, refused) = await asyncio.gather(
            answered_all((client.search(query, kind), client.name)
                         for client in self._sources.catalog_for(kind)),
            self._works.of_name(query, kind),
        )

        answers, refusals = split(outcomes)
        # Порция считается по выдаче, а не по странице: у каталога она стоит
        # одного запроса, у работ — одного на всех найденных тёзок разом, а их
        # бывают сотни, и показанная строка ложится в базу.
        #
        # Работы тёзок переплетаются между собой до того, как порция отрежет
        # лишнее: сложенные подряд, работы первого съедают её целиком, а решение
        # пользователя — «по имени ищутся работы всех людей с таким именем».
        #
        # Близнецы снимаются до среза и по той же паре, что и складывание своей
        # выдачи с чужой: однофамильцы бывают соавторами — Коэны, Руссо,
        # Вачовски, — и общая работа заняла бы по слоту на каждого. Складывание
        # снимает её позже, и до экрана доехала бы половина порции.
        together = unique_by(_weave(works),
                             lambda one: (one.source, one.source_id))
        woven = _weave([answer[:SEARCH_SIZE] for answer in answers]
                       + [together[:SEARCH_SIZE]])

        return ExternalSearch(
            views=tuple(await to_views(woven, self._genres, self._clock)),
            refusals=tuple(once(refusals + refused)),
        )
