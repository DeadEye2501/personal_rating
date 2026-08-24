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
from backend.app import build_backend
from backend.config import load_config
from backend.storage.session import create_engine
from backend.storage.tables import metadata
from tests.conftest import MOMENT, FakeSources, an_item, unreachable
from tests.wiring import search_service


async def assemble(tmp_path, transport=None):
    """Собранный бэкенд на своей базе и подставном транспорте.

    Здесь, а не в модуле проверок: его просят двое — обещание офлайна и
    проверки самой сборки, — и своими копиями они разъехались бы молча."""
    engine = create_engine(tmp_path / "library.db")
    async with engine.begin() as connection:
        await connection.run_sync(metadata.create_all)
    await engine.dispose()

    config = load_config({"DATA_DIR": str(tmp_path)}, base_dir=tmp_path)
    return await build_backend(config, transport=transport or unreachable())


@pytest.fixture
async def offline(tmp_path):
    """Собранный бэкенд без сети: транспорт по умолчанию не дозванивается."""
    backend = await assemble(tmp_path)
    yield backend
    await backend.aclose()


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
async def service(sessions):
    """Сервис поиска на подставных клиентах. Здесь, а не в двух модулях по
    копии: проверки выдачи и проверки жанров кандидата разъехались по файлам,
    когда первый упёрся в предел, — и обёртка уехала следом дважды."""
    return lambda *clients, covers=None: search_service(sessions, *clients,
                                                        covers=covers)


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
