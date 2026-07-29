"""Общая основа записи карточки в базу."""

from backend.model import Credit, SourceCard
from backend.service.posters import PosterService
from backend.storage.repository.credits import CreditRepository
from backend.storage.repository.external import (
    ExternalIdsRepository,
    ExternalRatingsRepository,
)
from backend.storage.repository.genres import GenresRepository
from backend.storage.repository.library import LibraryRepository


class CardParts:
    """Репозитории одной карточки и те её части, которые и запись, и привязка
    кладут одинаково: состав, чужие идентификаторы и оценки агрегаторов.

    Наследников двое — `CardWriter` и `Linker`, — и отличаются они не этими
    частями, а тем, что делают вокруг: первый убирает за собой при срыве,
    второй сливает поля и не трогает занятое."""

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

    async def _attach_credits(self, repository: CreditRepository, item_id: int,
                              credits: tuple[Credit, ...]) -> None:
        for credit in credits:
            entity_id = await repository.ensure(credit)
            await repository.attach(item_id, entity_id, credit.role,
                                    credit.position)

    async def _write_external(self, item_id: int, card: SourceCard) -> None:
        """Чем карточка известна чужим базам."""
        for external in card.external_ids:
            await self._ids.put(item_id, external)
        for rating in card.ratings:
            await self._ratings.record(item_id, rating)
