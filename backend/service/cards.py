"""Карточка источника строками базы."""

import asyncio
import logging

from backend.model import ItemExists, Refusal, SourceCard
from backend.service.card_parts import CardParts
from backend.service.creation import fresh_item
from backend.service.genres import resolved_genres
from backend.service.removal import remove_card
from backend.sources.errors import broken

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

        item_id = await self._started(card)
        if isinstance(item_id, Refusal):
            return item_id

        try:
            await self._write_the_rest(item_id, card, poster)
        except asyncio.CancelledError:
            # Отмена в `Exception` не попадает — она наследник `BaseException`, —
            # а приходит она штатно: так гасится загрузка при закрытии окна.
            # Без своей ветки в базе осталась бы карточка со свежим `synced_at`,
            # который утверждает, что на этот момент она была полной, — и
            # перезапроса не будет никогда. Отмену пробрасываем: гасят ею нас.
            logger.warning("запись карточки %s отменена, откатываю", item_id)
            await remove_card(self._library, self.posters, item_id)
            raise
        except Exception as error:
            # Ловим всё, а не один `IdentityTaken`. Последний шаг записи —
            # постер, а он ложится во второй файл базы, со своей дисковой
            # ошибкой и своей блокировкой. Оставить там строку карточки значит
            # получить ту самую частичную карточку, которой «не бывает»:
            # обложки нет, состава может не быть, а `synced_at` утверждает, что
            # на этот момент карточка была полной, — и перезапроса не будет,
            # потому что она свежая.
            logger.exception("откатываю карточку %s", item_id)
            await remove_card(self._library, self.posters, item_id)
            return broken(str(card.item.source), error)

        return item_id

    async def _started(self, card: SourceCard) -> int | Refusal:
        """Строка карточки — или отказ, если завести её не вышло.

        Наружу из писателя летит отказ, а не исключение: у границы потоков
        второго канала доставки нет. Ловится не один `ItemExists`, потому что
        заведение — это две базы, и вторая отвечает своими бедами: занятый файл,
        закрытое хранилище. Убирает за собой `fresh_item`, здесь остаётся
        назвать причину."""
        try:
            return await fresh_item(self._library, self.posters, card.item)
        except ItemExists as error:
            logger.warning("карточка уже в библиотеке: %s", error)
            return broken(str(card.item.source), error)
        except Exception as error:
            logger.exception("карточку %s завести не удалось", card.item.title)
            return broken(str(card.item.source), error)

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
