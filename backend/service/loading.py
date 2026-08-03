"""Кандидат превращается в карточку."""

import asyncio
import logging

from backend.model import (
    CardView,
    ExternalLink,
    Found,
    Missing,
    Reason,
    Refusal,
    Source,
    SourceCard,
)
from backend.service.asking import answered
from backend.service.cards import CardWriter
from backend.service.posters import PosterService
from backend.sources.registry import Sources
from backend.storage.repository.library import LibraryRepository

logger = logging.getLogger(__name__)


class Loader:
    """Всё, что карточка получает от источника после выдачи поиска.

    Это второй круг загрузки — детальный ответ и обложка разом, потом запись, —
    и путь по вставленной ссылке, где карточку добывают не из выдачи, а из
    адреса. Перезапрос по сроку живёт отдельно, в `service/series.py`: его
    заводят часы, а не человек."""

    def __init__(self, library: LibraryRepository, writer: CardWriter,
                 sources: Sources, posters: PosterService) -> None:
        self._library = library
        self._writer = writer
        self._sources = sources
        self._posters = posters

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

        existing = await self._library.find_by_source(view.kind, view.source, view.source_id)
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

        # Ответ карточки старше ответа обложки: упасть могут оба разом — они и
        # спрашиваются разом, — но «повторите позже» про исчезнувшую у источника
        # карточку это совет, которому нельзя последовать.
        if not isinstance(card, Found):
            return card
        if isinstance(poster, Refusal):
            # Не скачалась — карточка не пишется вовсе: повторим при следующем
            # показе. Отдельного случая тут нет, это общее правило.
            return poster

        if poster is None:
            poster = await self._second_try(card.value, view.poster_url)
            if isinstance(poster, Refusal):
                return poster

        return await self._writer.save(card.value, poster)

    async def _second_try(self, card: SourceCard,
                          asked: str) -> bytes | None | Refusal:
        """Вторая попытка за обложкой — по адресу детального ответа.

        Нужна потому, что круги идут разом: у кандидата выдачи адреса может не
        быть вовсе, а в детальном ответе он есть. И только по другому адресу: у
        Steam оба берутся из одного ответа `GetItems` и обычно совпадают, и
        повтор дал бы второй `404` на ту же картинку — а судьбу карточки решал бы
        уже он, превращая «обложки нет» в отказ на любой сетевой икоте."""
        if card.item.poster_url == asked:
            return None
        return await self._posters.fetch(card.item.source, card.item.poster_url)

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
