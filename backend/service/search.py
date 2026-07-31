"""Что найдётся по запросу."""

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime

from backend.model import (
    CardView,
    ExternalSearch,
    Kind,
    SearchHit,
)
from backend.service.asking import answered
from backend.service.hits import split, to_views
from backend.sources.registry import Sources
from backend.storage.repository.genres import GenresRepository
from backend.storage.repository.library import LibraryRepository
from backend.storage.repository.views import ViewsRepository

logger = logging.getLogger(__name__)

# Ровно страница выдачи TMDB: одна порция стоит одного запроса. Величина —
# настройка, а не свойство схемы.
SEARCH_SIZE = 20


def _weave(answers: list[list[SearchHit]]) -> list[SearchHit]:
    """Выдачи нескольких источников — вперемешку, по одному кандидату по кругу.

    У игр магазина два, и склеить их подряд нельзя: поиск GOG никогда не
    отвечает «не найдено» и на бессмыслицу отдаёт два десятка несвязанных игр.
    Подряд это значит, что вторая половина страницы — всегда мусор GOG, а его
    настоящие находки начинаются там, куда никто не доскроллит.

    Порядок внутри каждой выдачи сохраняется: он задан источником, и на
    единственной выдаче — у кино источник один — переплетение её и возвращает."""
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
        self._genres = genres
        # Часы внедряются, как во всех записях проекта: отметка бесплатной оценки
        # кандидата в базу не попадает, но брать время изнутри — путь к тому, что
        # однажды попадёт и проверить это будет нечем.
        self._clock = clock

    async def local(self, kind: Kind, query: str) -> list[CardView]:
        item_ids = await self._library.search(kind, query, limit=SEARCH_SIZE)
        return await self._views.in_order(item_ids)

    async def external(self, kind: Kind, query: str) -> ExternalSearch:
        """У игр магазина два, и спрашиваем их разом. Отказ одного не скрывает
        ответ другого."""
        clients = self._sources.catalog_for(kind)
        outcomes = await asyncio.gather(
            *(answered(client.search(query, kind), client.name)
              for client in clients)
        )

        answers, refusals = split(outcomes)
        # Порция считается по источнику: одна страница — один запрос.
        woven = _weave([answer[:SEARCH_SIZE] for answer in answers])

        return ExternalSearch(
            views=tuple(await to_views(woven, self._genres, self._clock)),
            refusals=tuple(refusals),
        )
