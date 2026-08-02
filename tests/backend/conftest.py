"""Фикстуры проверок бэкенда, общие у соседних модулей.

Здесь, а не в модуле-помощнике рядом: фикстуру нельзя импортировать — линтер
снимает её как неиспользуемую, — а `conftest.py` пакета pytest находит сам."""

import pytest

from backend.model import ExternalId, IdSource
from backend.service.enrich import Enricher
from backend.storage.repository.external import (
    ExternalIdsRepository,
    ExternalRatingsRepository,
)
from backend.storage.repository.library import LibraryRepository
from tests.conftest import MOMENT, FakeSources, an_item


@pytest.fixture
async def item_id(sessions):
    made = await LibraryRepository(sessions).create(
        an_item("157336", "Интерстеллар")
    )
    await ExternalIdsRepository(sessions).put(
        made, ExternalId(IdSource.IMDB, "tt0816692")
    )
    return made

@pytest.fixture
async def enrich(sessions):
    """Обогатитель с остановленными часами: сроки годности — предмет проверки."""

    def build(*clients) -> Enricher:
        return Enricher(
            sources=FakeSources(*clients),
            ids=ExternalIdsRepository(sessions),
            ratings=ExternalRatingsRepository(sessions),
            clock=lambda: MOMENT,
        )

    return build
