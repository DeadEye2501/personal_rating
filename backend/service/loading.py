"""Кандидат превращается в карточку."""

import asyncio
import logging

from backend.model import CardView
from backend.service.asking import answered
from backend.service.cards import CardWriter
from backend.service.posters import PosterService
from backend.sources.errors import Found, Missing, Reason, Refusal
from backend.sources.registry import Sources
from backend.storage.repository.library import LibraryRepository

logger = logging.getLogger(__name__)


class Loader:
    """Три круга загрузки. Первый — выдача поиска, она уже позади: на входе
    кандидат. Здесь второй, детальный ответ и обложка разом, и запись."""

    def __init__(self, library: LibraryRepository, writer: CardWriter,
                 sources: Sources, posters: PosterService) -> None:
        self._library = library
        self._writer = writer
        self._sources = sources
        self._posters = posters

    async def ensure(self, view: CardView) -> int | Missing | Refusal:
        """Идентификатор карточки в базе: уже лежавшей или только что
        записанной. `Missing` — источник её больше не знает."""
        if view.item_id is not None:
            return view.item_id

        existing = await self._library.find_by_source(view.source, view.source_id)
        if existing is not None:
            return existing.id

        client = self._sources.client_for(view.source)
        if client is None:
            logger.warning("нечем загрузить карточку источника %s", view.source)
            return Refusal(source=str(view.source), reason=Reason.BROKEN,
                           detail=f"нет каталожного клиента для {view.source}")

        # Круги 2а и 2б: адрес обложки пришёл ещё с выдачей поиска, поэтому
        # детальный ответ её не ждёт.
        card, poster = await asyncio.gather(
            answered(client.card(view.source_id, view.kind), client.name),
            answered(self._posters.fetch(view.source, view.poster_url),
                     client.name),
        )

        if isinstance(poster, Refusal):
            # Не скачалась — карточка не пишется вовсе: повторим при следующем
            # показе. Отдельного случая тут нет, это общее правило.
            return poster
        if not isinstance(card, Found):
            return card

        return await self._writer.save(card.value, poster)
