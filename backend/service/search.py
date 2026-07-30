"""Что найдётся по запросу."""

import asyncio
import logging
from dataclasses import dataclass

from backend.model import (
    CardView,
    Genre,
    GenreSource,
    Kind,
    SearchHit,
    view_from_hit,
)
from backend.sources.errors import Found, Reason, Refusal
from backend.sources.registry import Sources
from backend.storage.repository.genres import GenresRepository
from backend.storage.repository.library import LibraryRepository
from backend.storage.repository.views import ViewsRepository

logger = logging.getLogger(__name__)

# Ровно страница выдачи TMDB: одна порция стоит одного запроса. Величина —
# настройка, а не свойство схемы.
SEARCH_SIZE = 20


@dataclass(frozen=True, slots=True)
class ExternalSearch:
    """Что ответила внешняя база. Отказ — поле в результате, а не исключение: у
    границы потоков второго канала доставки нет."""

    views: tuple[CardView, ...]
    refusals: tuple[Refusal, ...]


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
                 sources: Sources, genres: GenresRepository) -> None:
        self._library = library
        self._views = views
        self._sources = sources
        self._genres = genres

    async def local(self, kind: Kind, query: str) -> list[CardView]:
        item_ids = await self._library.search(kind, query, limit=SEARCH_SIZE)
        return await self._views.in_order(item_ids)

    async def external(self, kind: Kind, query: str) -> ExternalSearch:
        """У игр магазина два, и спрашиваем их разом. Отказ одного не скрывает
        ответ другого."""
        clients = self._sources.catalog_for(kind)
        # return_exceptions обязателен. `SourceHttp.get` ловит только
        # `httpx.HTTPError`; всё, что сломается вне его — разбор, чужая
        # библиотека, наша опечатка, — улетело бы из сервиса наружу, вопреки
        # правилу «исключений из сервисов не летит». А заодно второй запрос
        # остался бы недождавшимся, с `Task exception was never retrieved`.
        outcomes = await asyncio.gather(
            *(client.search(query, kind) for client in clients),
            return_exceptions=True,
        )

        answers: list[list[SearchHit]] = []
        refusals: list[Refusal] = []
        for client, outcome in zip(clients, outcomes, strict=True):
            if isinstance(outcome, BaseException):
                refusals.append(self._broke(client, outcome))
            elif isinstance(outcome, Refusal):
                refusals.append(outcome)
            elif isinstance(outcome, Found):
                # Порция считается по источнику: одна страница — один запрос.
                answers.append(list(outcome.value[:SEARCH_SIZE]))

        return ExternalSearch(views=tuple(await self._to_views(_weave(answers))),
                              refusals=tuple(refusals))

    def _broke(self, client, error: BaseException) -> Refusal:
        """Имя источника, а не repr клиента: `Refusal.source` уезжает в клиент и
        оттуда в плашку сообщений, и «<TmdbClient object at 0x...>» человеку
        показывать нечего."""
        logger.exception("поиск в %s сорвался", client.name, exc_info=error)
        return Refusal(source=client.name, reason=Reason.BROKEN,
                       detail=str(error))

    async def _to_views(self, hits: list[SearchHit]) -> list[CardView]:
        index: dict[GenreSource, dict[str, tuple[Genre, ...]]] = {}
        views = []
        for hit in hits:
            for space, _ in hit.genre_ext_ids:
                if space not in index:
                    index[space] = await self._genres.index(space)
            views.append(view_from_hit(hit, _genres_of(hit, index)))
        return views


def _genres_of(
    hit: SearchHit,
    index: dict[GenreSource, dict[str, tuple[Genre, ...]]],
) -> tuple[Genre, ...]:
    """Незнакомое молча отбрасывается: заводить жанр на лету нельзя — имена в
    справочнике наши, а сборный жанр автоматически не разложить."""
    found: list[Genre] = []
    for space, ext_id in hit.genre_ext_ids:
        for genre in index[space].get(ext_id, ()):
            if genre not in found:
                found.append(genre)
    return tuple(found)
