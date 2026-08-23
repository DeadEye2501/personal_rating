"""Что найдётся по человеку или студии.

Отдельно от `search.py`: тот ищет по строке запроса и спрашивает каталожных
клиентов вида, а этот ищет по строке человека в базе и знает про внешнюю
идентичность. Общее у них — чужие работы по имени и сборка кандидатов в
карточки, и то и другое уже вынесено."""

from collections.abc import Callable
from datetime import datetime

from backend.model import (
    CardView,
    ExternalSearch,
    Kind,
    Refusal,
    SearchHit,
    Source,
    merge_results,
)
from backend.service.filmography import Filmographies
from backend.service.hits import to_views, without_removed
from backend.service.search import SearchParts
from backend.sources.registry import Sources
from backend.storage.repository.credits import CreditRepository
from backend.storage.repository.views import ViewsRepository


class PeopleSearch:
    """Внутренняя половина всегда идёт по строке в базе, внешняя ветвится по
    наличию внешней идентичности."""

    def __init__(self, views: ViewsRepository, people: CreditRepository,
                 companies: CreditRepository, sources: Sources,
                 parts: SearchParts,
                 clock: Callable[[], datetime] = datetime.now) -> None:
        self._views = views
        self._entities = {"people": people, "companies": companies}
        self._works = Filmographies(sources)
        self._genres = parts.genres
        self._removed = parts.removed
        self._clock = clock

    async def by_entity(self, domain: str, entity_id: int,
                        kind: Kind) -> ExternalSearch:
        repository = self._entities[domain]
        identity = await repository.identity_of(entity_id)
        if identity is None:
            return ExternalSearch(views=(), refusals=())

        own = await self._own(repository, entity_id, kind)
        hits, refusals = await self._outside(domain, identity, kind)
        # Убранное не возвращается и этим жестом тоже: «больше не приходит
        # никогда» сказано про игру, а не про строку поиска. Отсев тот же, что
        # у строки, и стоит он до сборки карточек — на удалённого кандидата не
        # уходит ни одного запроса за жанрами.
        hits, = await without_removed(self._removed, [hits])
        outside = await to_views(hits, self._genres, self._clock)
        return ExternalSearch(views=tuple(merge_results(own, outside)),
                              refusals=tuple(refusals))

    async def _own(self, repository: CreditRepository, entity_id: int,
                   kind: Kind) -> list[CardView]:
        """По строке человека, а не по имени: имя тёзку не различает, и клик
        притащил бы и чужие работы, и карточку, которая просто так
        называется."""
        return await self._views.in_order(
            await repository.items_of(entity_id, kind))

    async def _outside(self, domain: str,
                       identity: tuple[str, str | None, Source | None],
                       kind: Kind) -> tuple[list[SearchHit], list[Refusal]]:
        """У студий внешней половины нет вовсе, и решается это доменом, а не
        видом: ручки, по которой спрашивают компанию, нет ни у одного источника,
        а `/search/person` с названием студии привёз бы фильмографию
        однофамильца."""
        if domain == "companies":
            return [], []

        name, source_id, source = identity
        # Номер отдаётся наружу только своему источнику: чужой уехал бы в запрос
        # как есть и не нашёл бы ничего — молча, без единого отказа.
        works, refusals = (
            await self._works.of_person(source_id, kind)
            if source_id and self._works.owns(source, kind)
            else await self._works.of_name(name, kind))
        # Подряд, а не переплетением: у клика порции нет — показываются все
        # работы всех тёзок, — и человек читает их по одному человеку за раз.
        # Переплетает их строка поиска, где порция двадцать строк.
        return [one for works_of_one in works for one in works_of_one], refusals
