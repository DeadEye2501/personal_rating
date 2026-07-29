"""Кинопоиск снаружи: одно имя над двумя зеркалами."""

import logging

from backend.model import Kind
from backend.sources.errors import Outcome, Refusal
from backend.sources.ratings.kinopoisk.poiskkino import PoiskkinoClient
from backend.sources.ratings.kinopoisk.unofficial import UnofficialClient

logger = logging.getLogger(__name__)


class KinopoiskClient:
    """Зеркала отдают одни и те же данные под одним идентификатором — второе
    нужно на случай, когда первое закроется."""

    def __init__(self, primary: PoiskkinoClient, fallback: UnofficialClient) -> None:
        self._primary = primary
        self._fallback = fallback

    async def ratings(self, imdb_id: str, kind: Kind) -> Outcome:
        result = await self._primary.ratings(imdb_id, kind)
        if not isinstance(result, Refusal):
            # Честное «такого нет» — это ответ. Второе зеркало не спрашиваем,
            # иначе каждый промах стоил бы двух запросов из пятисот в сутки.
            return result

        logger.info(
            "kinopoisk: основное зеркало отказало (%s), беру запасное", result.reason
        )
        return await self._fallback.ratings(imdb_id, kind)

    async def aclose(self) -> None:
        await self._primary.aclose()
        await self._fallback.aclose()
