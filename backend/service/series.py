"""Перезапрос сериала по сроку годности."""

import logging
from collections.abc import Callable
from datetime import datetime, timedelta

from backend.model import Found, Kind, Missing, Source
from backend.service.asking import answered
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


class SeriesRefresh:
    """Отдельно от загрузки: та добывает карточку у источника по требованию
    человека, а это единственное, что бэкенд перезапрашивает сам и по времени."""

    def __init__(self, library: LibraryRepository, sources: Sources,
                 clock: Callable[[], datetime] = datetime.now) -> None:
        self._library = library
        self._sources = sources
        self._clock = clock

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
