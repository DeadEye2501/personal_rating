"""Кандидат превращается в карточку."""

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, timedelta

from backend.model import CardView, ExternalLink, Kind, Source, SourceCard
from backend.service.asking import answered
from backend.service.cards import CardWriter
from backend.service.posters import PosterService
from backend.sources.errors import Found, Missing, Reason, Refusal
from backend.sources.registry import Sources
from backend.storage.repository.library import LibraryRepository

logger = logging.getLogger(__name__)

# Срок тот же, что у оценок со значением. Перезапрашиваем только видимые
# карточки: невидимых может быть тысяча.
REFRESH_TTL = timedelta(days=30)


def _kept(fresh: int | None, stored: int | None) -> int | None:
    """Не приехавшее число не стирает известное: сезоны у сериала уже были, и
    неполный ответ источника — не повод их забыть."""
    return fresh if fresh is not None else stored


class Loader:
    """Всё, что карточка получает от источника после выдачи поиска.

    Это второй круг загрузки — детальный ответ и обложка разом, потом запись, —
    единственный перезапрос по сроку, у сериала растут сезоны и серии, и путь по
    вставленной ссылке, где карточку добывают не из выдачи, а из адреса."""

    def __init__(self, library: LibraryRepository, writer: CardWriter,
                 sources: Sources, posters: PosterService,
                 clock: Callable[[], datetime] = datetime.now) -> None:
        self._library = library
        self._writer = writer
        self._sources = sources
        self._posters = posters
        self._clock = clock

    def _catalog(self, source: Source, action: str):
        """Каталожный клиент источника — или отказ вместо него.

        У ручной карточки клиента нет и быть не может: она ниоткуда не
        приезжала. `action` попадает в лог: спрашивают клиента двое, и по
        сообщению должно быть видно, кто именно не смог."""
        client = self._sources.client_for(source)
        if client is not None:
            return client
        logger.warning("нечем %s: источник %s", action, source)
        return Refusal(source=str(source), reason=Reason.BROKEN,
                       detail=f"нет каталожного клиента для {source}")

    async def ensure(self, view: CardView) -> int | Missing | Refusal:
        """Идентификатор карточки в базе: уже лежавшей или только что
        записанной. `Missing` — источник её больше не знает."""
        if view.item_id is not None:
            return view.item_id

        existing = await self._library.find_by_source(view.source, view.source_id)
        if existing is not None:
            return existing.id

        client = self._catalog(view.source, "загрузить карточку")
        if isinstance(client, Refusal):
            return client

        # Круги 2а и 2б: адрес обложки пришёл ещё с выдачей поиска, поэтому
        # детальный ответ её не ждёт.
        card, poster = await asyncio.gather(
            answered(client.card(view.source_id, view.kind), client.name),
            self._posters.fetch(view.source, view.poster_url),
        )

        if isinstance(poster, Refusal):
            # Не скачалась — карточка не пишется вовсе: повторим при следующем
            # показе. Отдельного случая тут нет, это общее правило.
            return poster
        if not isinstance(card, Found):
            return card

        return await self._writer.save(card.value, poster)

    async def card_for_link(
        self, link: ExternalLink
    ) -> SourceCard | Missing | Refusal:
        """Разобранная ссылка — в карточку источника, готовую для привязки.

        Единственное место, где адрес не совпадает с идентичностью: у GOG в
        ссылке слаг, а каталогу нужен номер."""
        client = self._catalog(link.source, "сходить по ссылке")
        if isinstance(client, Refusal):
            return client

        source_id = link.source_id
        if link.source is Source.GOG:
            resolved = await answered(client.resolve_slug(source_id), client.name)
            if not isinstance(resolved, Found):
                return resolved
            source_id = resolved.value

        outcome = await answered(client.card(source_id, link.kind), client.name)
        return outcome.value if isinstance(outcome, Found) else outcome

    async def refresh(self, item_id: int) -> None:
        """Число сезонов и серий у сериала — единственное, что
        перезапрашивается. Всё остальное с момента создания карточки принадлежит
        тебе."""
        item = await self._library.get(item_id)
        if item is None or item.kind is not Kind.SERIES:
            return
        if item.source is not Source.TMDB:
            # Ручной карточке перезапрашивать нечего: она ниоткуда не приезжала.
            return
        if self._clock() - item.synced_at <= REFRESH_TTL:
            return

        client = self._sources.client_for(item.source)
        outcome = await answered(client.series_counts(item.source_id), client.name)
        if isinstance(outcome, Missing):
            logger.warning("TMDB больше не знает сериал %s", item.source_id)
            return
        if not isinstance(outcome, Found):
            # Отказ — состояние данных: повторим при следующем показе.
            return

        await self._library.refresh_series_counts(
            item_id,
            _kept(outcome.value.seasons, item.seasons_count),
            _kept(outcome.value.episodes, item.episodes_count),
            now=self._clock(),
        )
