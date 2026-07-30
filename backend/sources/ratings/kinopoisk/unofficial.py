"""Запасное зеркало Кинопоиска."""

import logging

import httpx

from backend.model import Kind
from backend.sources.errors import Outcome, parsed
from backend.sources.http import SourceHttp
from backend.sources.ratings.kinopoisk.mirror import (
    SOURCE,
    answered,
    refuse_code,
    refuse_key,
    refuse_quota,
    refuse_rate,
)
from backend.sources.ratings.kinopoisk.parse import parse_unofficial

logger = logging.getLogger(__name__)

# Именно /films, а не search-by-keyword: у второго 404 означает и «фильм не
# найден», и «поиск ничего не дал» — два разных смысла в одном коде.
BASE = "https://kinopoiskapiunofficial.tech/api/v2.2/films"


class UnofficialClient:
    def __init__(self, http: SourceHttp, api_key: str) -> None:
        self._http = http
        self._key = api_key

    async def ratings(self, imdb_id: str, kind: Kind) -> Outcome:
        response = await self._http.get(
            BASE,
            params={"imdbId": imdb_id},  # префикс tt обязателен
            headers={"X-API-KEY": self._key},
        )
        if not isinstance(response, httpx.Response):
            return response
        return self._verdict(response)

    def _verdict(self, response: httpx.Response) -> Outcome:
        status = response.status_code
        if status == 402:
            return refuse_quota(self._http)
        if status == 429:
            # Может прийти от nginx с телом text/html — JSON не разбираем.
            return refuse_rate(self._http)
        if status == 401:
            return refuse_key()
        if status != 200:
            return refuse_code(status)

        return parsed(logger, SOURCE, "ответ запасного зеркала не разобрался",
                      lambda: answered(parse_unofficial(response.json())))

    async def aclose(self) -> None:
        await self._http.aclose()
