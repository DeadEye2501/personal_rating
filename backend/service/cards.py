"""Карточка источника строками базы."""

import logging

from backend.model import Credit, SourceCard
from backend.service.genres import resolved_genres
from backend.service.posters import PosterService
from backend.sources.errors import Refusal, broken
from backend.storage.repository.credits import CreditRepository
from backend.storage.repository.external import (
    ExternalIdsRepository,
    ExternalRatingsRepository,
)
from backend.storage.repository.genres import GenresRepository
from backend.storage.repository.library import ItemExists, LibraryRepository

logger = logging.getLogger(__name__)


class CardWriter:
    """Порядок задан правилом «частичной карточки не бывает»: сначала добываем
    обложку, и только потом пишем. Если запись сорвалась на середине — убираем
    за собой: общей транзакции на два файла базы не бывает."""

    def __init__(
        self,
        library: LibraryRepository,
        genres: GenresRepository,
        people: CreditRepository,
        companies: CreditRepository,
        ids: ExternalIdsRepository,
        ratings: ExternalRatingsRepository,
        posters: PosterService,
    ) -> None:
        self._library = library
        self._genres = genres
        self._people = people
        self._companies = companies
        self._ids = ids
        self._ratings = ratings
        self.posters = posters

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

        await self._attach(self._people, item_id, card.people)
        await self._attach(self._companies, item_id, card.companies)

        for external in card.external_ids:
            await self._ids.put(item_id, external)
        for rating in card.ratings:
            await self._ratings.record(item_id, rating)

        if poster is not None:
            await self.posters.save(item_id, poster, card.item.synced_at)

    async def _attach(self, repository: CreditRepository, item_id: int,
                      credits: tuple[Credit, ...]) -> None:
        for credit in credits:
            entity_id = await repository.ensure(credit)
            await repository.attach(item_id, entity_id, credit.role,
                                    credit.position)
