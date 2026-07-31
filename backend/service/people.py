"""Что найдётся по человеку или студии.

Отдельно от `search.py`: тот ищет по строке запроса и спрашивает каталожных
клиентов вида, а этот ищет по строке человека в базе и знает про внешнюю
идентичность. Общее у них — складывание двух выдач и сборка кандидатов в
карточки, и то и другое уже вынесено."""

import asyncio
from collections.abc import Callable
from datetime import datetime

from backend.model import (
    CardView,
    ExternalSearch,
    Found,
    Kind,
    Refusal,
    merge_results,
)
from backend.service.asking import answered
from backend.service.hits import split, to_views
from backend.sources.registry import Sources
from backend.storage.repository.credits import CreditRepository
from backend.storage.repository.genres import GenresRepository
from backend.storage.repository.views import ViewsRepository
from backend.unique import unique_by


def _once(refusals: list[Refusal]) -> list[Refusal]:
    """Один отказ на источник и причину. Спросили пятерых найденных, лёг
    источник — плашка внизу всё равно говорит про источник, а он тут один.

    Ключом, а не целиком: у сетевого отказа в `detail` стоит текст ошибки с
    адресом, и пять одинаковых по сути отказов вышли бы пятью разными."""
    return unique_by(refusals, lambda one: (one.source, one.reason))


class PeopleSearch:
    """Внутренняя половина всегда идёт по строке в базе, внешняя ветвится по
    наличию внешней идентичности."""

    def __init__(self, views: ViewsRepository, people: CreditRepository,
                 companies: CreditRepository, sources: Sources,
                 genres: GenresRepository,
                 clock: Callable[[], datetime] = datetime.now) -> None:
        self._views = views
        self._entities = {"people": people, "companies": companies}
        self._sources = sources
        self._genres = genres
        self._clock = clock

    async def by_entity(self, domain: str, entity_id: int,
                        kind: Kind) -> ExternalSearch:
        repository = self._entities[domain]
        identity = await repository.identity_of(entity_id)
        if identity is None:
            return ExternalSearch(views=(), refusals=())

        own = await self._own(repository, entity_id, kind)
        outside, refusals = await self._outside(domain, identity, kind)
        return ExternalSearch(views=tuple(merge_results(own, outside)),
                              refusals=tuple(refusals))

    async def _own(self, repository: CreditRepository, entity_id: int,
                   kind: Kind) -> list[CardView]:
        """По строке человека, а не по имени: имя тёзку не различает, и клик
        притащил бы и чужие работы, и карточку, которая просто так
        называется."""
        return await self._views.in_order(
            await repository.items_of(entity_id, kind))

    async def _outside(self, domain: str, identity: tuple[str, str | None],
                       kind: Kind) -> tuple[list[CardView], list[Refusal]]:
        """Наружу ходят только за людьми, и только если клиент вида есть —
        решает это реестр, там же и замер про магазины.

        У студий внешней половины нет вовсе, и решается это доменом, а не видом:
        ручки, по которой спрашивают компанию, нет ни у одного источника, а
        `/search/person` с названием студии привёз бы фильмографию однофамильца."""
        if domain == "companies":
            return [], []

        client = self._sources.people_for(kind)
        if client is None:
            return [], []

        name, source_id = identity
        if source_id:
            return await self._works(client, [source_id], kind)
        if not name.strip():
            # Пустое имя в базе разрешено, а спрашивать по нему нечего: ушёл бы
            # пустой `query` и вернулся отказ, который не о чем.
            return [], []

        found = await answered(client.find_people(name), client.name)
        if isinstance(found, Refusal):
            return [], [found]
        if not isinstance(found, Found):
            return [], []
        return await self._works(client, [one.source_id for one in found.value],
                                 kind)

    async def _works(self, client, person_ids: list[str],
                     kind: Kind) -> tuple[list[CardView], list[Refusal]]:
        """Фильмографии всех найденных разом: их бывает несколько, и ждать по
        очереди значило бы сложить их сроки ожидания."""
        outcomes = await asyncio.gather(
            *(answered(client.credits_of(person_id, kind), client.name)
              for person_id in person_ids)
        )

        answers, refusals = split(outcomes)
        hits = [one for answer in answers for one in answer]
        return await to_views(hits, self._genres, self._clock), _once(refusals)
