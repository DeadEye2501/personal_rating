"""Карточка источника строками базы."""

import logging

from backend.model import SourceCard
from backend.service.card_parts import CardParts
from backend.service.genres import resolved_genres
from backend.sources.errors import Refusal, broken
from backend.storage.repository.library import ItemExists

logger = logging.getLogger(__name__)


class CardWriter(CardParts):
    """Порядок задан правилом «частичной карточки не бывает»: сначала добываем
    обложку, и только потом пишем. Если запись сорвалась на середине — убираем
    за собой: общей транзакции на два файла базы не бывает."""

    async def save(self, card: SourceCard,
                   poster: bytes | None = None) -> int | Refusal:
        if poster is None:
            poster = await self.posters.fetch(card.item.source,
                                              card.item.poster_url)
            if isinstance(poster, Refusal):
                # Не скачалась — не пишем ничего, повторим при следующем показе.
                return poster

        try:
            item_id = await self._library.create(card.item)
        except ItemExists as error:
            logger.warning("карточка уже в библиотеке: %s", error)
            return broken(str(card.item.source), error)

        try:
            await self._write_the_rest(item_id, card, poster)
        except Exception as error:
            # Ловим всё, а не один `IdentityTaken`. Последний шаг записи —
            # постер, а он ложится во второй файл базы, со своей дисковой
            # ошибкой и своей блокировкой. Оставить там строку карточки значит
            # получить ту самую частичную карточку, которой «не бывает»:
            # обложки нет, состава может не быть, а `synced_at` утверждает, что
            # на этот момент карточка была полной, — и перезапроса не будет,
            # потому что она свежая.
            logger.exception("откатываю карточку %s", item_id)
            await self._library.delete(item_id, self.posters.store)
            return broken(str(card.item.source), error)

        return item_id

    async def _write_the_rest(self, item_id: int, card: SourceCard,
                              poster: bytes | None) -> None:
        await self._genres.set_for_item(
            item_id, await resolved_genres(self._genres, card.genre_ext_ids)
        )

        await self._attach_credits(self._people, item_id, card.people)
        await self._attach_credits(self._companies, item_id, card.companies)

        await self._write_external(item_id, card)

        if poster is not None:
            await self.posters.save(item_id, poster, card.item.synced_at)
