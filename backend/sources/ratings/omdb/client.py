"""Разговор с OMDB по сети."""

import logging
from datetime import datetime, timedelta
from typing import ClassVar

import httpx

from backend.model import Kind, RatingSource
from backend.sources.errors import (
    BROKEN_BY_PARSING,
    Found,
    Missing,
    Outcome,
    Reason,
    Refusal,
    broken,
)
from backend.sources.http import SourceHttp
from backend.sources.ratings.omdb.parse import parse_ratings

logger = logging.getLogger(__name__)

BASE = "https://www.omdbapi.com/"


def until_midnight(now: datetime) -> timedelta:
    """Квота суточная, заголовков OMDB не отдаёт. Пробовать раньше
    бессмысленно: придёт тот же отказ, а потраченный запрос не вернуть."""
    tomorrow = (now + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return tomorrow - now


class OmdbClient:
    PROVIDES: ClassVar[tuple[RatingSource, ...]] = (
        RatingSource.IMDB,
        RatingSource.ROTTEN,
        RatingSource.METACRITIC,
    )

    def __init__(self, http: SourceHttp, api_key: str) -> None:
        self._http = http
        self._key = api_key

    @property
    def name(self) -> str:
        """Под этим именем источник назовётся в отказе — в том числе в отказе,
        который соберёт не он сам, а поймавший его исключение сервис."""
        return self._http.name

    async def ratings(self, imdb_id: str, kind: Kind) -> Outcome:
        response = await self._http.get(
            BASE, params={"apikey": self._key, "i": imdb_id}
        )
        if not isinstance(response, httpx.Response):
            return response

        try:
            payload = response.json()
        except ValueError as error:
            return broken("omdb", error)

        # Разобралось — ещё не значит объект: массив, число и строка тоже
        # валидный JSON, а `.get` есть только у словаря.
        if not isinstance(payload, dict):
            return Refusal(
                source="omdb", reason=Reason.BROKEN, detail="тело не объект"
            )

        if response.status_code == 200:
            return self._answer(payload)
        if response.status_code == 401:
            return self._denied(payload)
        return Refusal(
            source="omdb",
            reason=Reason.BROKEN,
            detail=f"HTTP {response.status_code}",
        )

    def _answer(self, payload: dict) -> Outcome:
        """Сначала код, потом текст: под 200 текст `Error` бывает трёх видов —
        «Movie not found!», «Error getting data.», «Incorrect IMDb ID.» — и все
        три означают одно и то же."""
        if payload.get("Response") == "False":
            return Missing()
        try:
            return Found(parse_ratings(payload))
        except BROKEN_BY_PARSING as error:
            logger.warning("omdb: ответ не разобрался — %s", error)
            return broken("omdb", error)

    def _denied(self, payload: dict) -> Refusal:
        """Под кодом 401 живут две разные беды, и различает их только текст.
        Ищем подстроку нестрого: точные формулировки взяты из issue-трекера, а
        не из документации."""
        error = (payload.get("Error") or "").lower()
        if "limit" in error:
            delay = until_midnight(self._http.clock())
            self._http.breaker.trip(delay)
            return Refusal(source="omdb", reason=Reason.QUOTA, retry_after=delay)
        if "key" in error:
            # Предохранитель не взводим: битый ключ сроком не лечится, и закрыв
            # источник на сутки, мы не дали бы человеку вписать новый.
            return Refusal(source="omdb", reason=Reason.KEY, detail=error)
        # Полного списка значений `Error` не существует: неизвестный 401 считаем
        # временным, чтобы не объявить рабочий ключ битым.
        logger.warning("omdb: незнакомый 401 — %s", error)
        return Refusal(source="omdb", reason=Reason.BROKEN, detail=error)

    async def aclose(self) -> None:
        await self._http.aclose()
