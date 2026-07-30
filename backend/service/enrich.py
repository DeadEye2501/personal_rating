"""Чужие оценки у карточки."""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from backend.model import ExternalId, ExternalRating, IdSource, Kind, RatingSource
from backend.service.asking import answered
from backend.sources.errors import Found, Refusal
from backend.sources.registry import Sources
from backend.storage.repository.external import (
    ExternalIdsRepository,
    ExternalIdTaken,
    ExternalRatingsRepository,
)
from backend.unique import unique

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class _Harvest:
    """Что дал круг опроса: найденные значения и источники, по которым
    спрашивать было некого.

    Отдельного списка ответивших не нужно: каждый просроченный источник объявлен
    хотя бы одним спрошенным клиентом, а тот либо отказал, либо ответил. Значит
    «про него не ответил никто» — это ровно «все, кто его знает, отказали»."""

    values: dict[RatingSource, float] = field(default_factory=dict)
    refused: set[RatingSource] = field(default_factory=set)


class Enricher:
    """Третий круг: чужие оценки. Идёт после второго не по удобству, а по
    данным — `imdb_id` есть только в детальном ответе.

    Здесь производится второе из трёх состояний `external_rating`: строка с
    пустым значением, «спрашивали, у источника нет»."""

    def __init__(self, sources: Sources, ids: ExternalIdsRepository,
                 ratings: ExternalRatingsRepository,
                 clock: Callable[[], datetime] = datetime.now) -> None:
        self._sources = sources
        self._ids = ids
        self._ratings = ratings
        self._clock = clock

    async def enrich(self, item_id: int, kind: Kind) -> list[ExternalRating]:
        """Состояние оценок после обогащения — то, что показывать."""
        now = self._clock()
        # Просроченного нет — читать больше нечего. У игр сюда попадает пустой
        # список ожидаемых: оценки им приезжают вместе с карточкой. Выход
        # ранний, потому что дальше идёт запрос за `imdb_id`, а карточек на
        # странице пятьдесят.
        stale = await self._ratings.stale_sources(item_id, self.expected(kind),
                                                  now)
        if not stale:
            return await self._ratings.ratings_of(item_id)

        imdb_id = await self._imdb_id(item_id)
        if imdb_id is None:
            logger.info("карточка %s без imdb_id: агрегаторов спросить нечем",
                        item_id)
            return await self._ratings.ratings_of(item_id)

        asked = [client for client in self._sources.rating_sources(kind)
                 if set(client.PROVIDES) & set(stale)]
        outcomes = await asyncio.gather(
            *(answered(client.ratings(imdb_id, kind), client.name)
              for client in asked)
        )

        harvest = await self._harvested(item_id, asked, outcomes)
        await self._record(item_id, harvest, stale, now)
        return await self._ratings.ratings_of(item_id)

    def expected(self, kind: Kind) -> list[RatingSource]:
        """Кого вообще спрашивают у этого типа содержимого.

        Нужно показу: пока ответы едут, на их месте крутится кольцо, а вычесть
        приехавшее из ожидаемого можно только зная второе. Внутри бэкенда это
        известно, снаружи — нет."""
        return unique(source
                      for client in self._sources.rating_sources(kind)
                      for source in client.PROVIDES)

    async def _imdb_id(self, item_id: int) -> str | None:
        for external in await self._ids.ids_of(item_id):
            if external.source is IdSource.IMDB:
                return external.value
        return None

    async def _harvested(self, item_id: int, asked: list,
                         outcomes: list) -> _Harvest:
        harvest = _Harvest()
        for client, outcome in zip(asked, outcomes, strict=True):
            if isinstance(outcome, Refusal):
                # Отказ не пишется никогда — ни значением, ни пустотой. Сюда же
                # попадает сорвавшийся клиент: до ответа он не дошёл.
                harvest.refused.update(client.PROVIDES)
                continue
            # Missing сюда не доходит: источник ответил, что такого не знает, и
            # это и есть право написать пустое значение.
            if isinstance(outcome, Found):
                self._take(harvest, outcome.value.values, client.PROVIDES)
                for external in outcome.value.external_ids:
                    await self._keep(item_id, external)
        return harvest

    @staticmethod
    def _take(harvest: _Harvest, values: tuple[ExternalRating, ...],
              provides: tuple[RatingSource, ...]) -> None:
        """Побеждает тот, кого спросили первым: иначе значение зависело бы от
        того, кто быстрее ответил по сети. Пустое значение при этом места не
        занимает — «у него нет» уступает настоящему числу второго источника.

        Необъявленную оценку не берём: на `PROVIDES` стоит и запись пустого
        значения, и подсчёт ожидаемого, и двух правд про один источник быть не
        должно."""
        for rating in values:
            if rating.source not in provides:
                logger.warning("оценка %s пришла от того, кто её не обещал",
                               rating.source)
                continue
            if rating.value is not None and rating.source not in harvest.values:
                harvest.values[rating.source] = rating.value

    async def _record(self, item_id: int, harvest: _Harvest,
                      stale: list[RatingSource], now: datetime) -> None:
        # Значение пишем и то, которого не просили: оно уже приехало даром.
        for source, value in harvest.values.items():
            await self._ratings.record(item_id,
                                       ExternalRating(source, value, now))

        for source in stale:
            if source in harvest.values or source in harvest.refused:
                # Отказавший знающий источник — это «не смогли посмотреть», а не
                # «такого нет». Пустоту тут писать нельзя.
                continue
            await self._ratings.record(item_id, ExternalRating(source, None, now))

    async def _keep(self, item_id: int, external: ExternalId) -> None:
        try:
            await self._ids.put(item_id, external)
        except ExternalIdTaken as error:
            logger.warning("идентификатор %s занят: %s", external.value, error)
