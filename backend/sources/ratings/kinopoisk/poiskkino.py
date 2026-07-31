"""Основное зеркало Кинопоиска."""

import logging

import httpx

from backend.model import Kind, Outcome
from backend.sources.errors import absent, parsed
from backend.sources.http import SourceHttp
from backend.sources.ratings.kinopoisk.mirror import (
    SOURCE,
    answered,
    refuse_code,
    refuse_key,
    refuse_quota,
    refuse_rate,
)
from backend.sources.ratings.kinopoisk.parse import parse_poiskkino

logger = logging.getLogger(__name__)

BASE = "https://api.poiskkino.dev/v1.4/movie"
# Эти поля надо запрашивать явно, иначе их в ответе не будет.
FIELDS = ("id", "externalId", "rating")


class PoiskkinoClient:
    """Классифицируем по HTTP-коду, а не по числу в теле: в их спецификации у
    `404` указан тип ошибки `403`, и пример под заголовком «Фильм не найден»
    показывает тело «Превышен дневной лимит!». Телу здесь верить нельзя."""

    def __init__(self, http: SourceHttp, api_key: str) -> None:
        self._http = http
        self._key = api_key

    async def ratings(self, imdb_id: str, kind: Kind) -> Outcome:
        response = await self._http.get(
            BASE,
            params={"externalId.imdb": imdb_id, "selectFields": list(FIELDS)},
            headers={"X-API-KEY": self._key},
        )
        if not isinstance(response, httpx.Response):
            return response
        return self._verdict(response)

    def _verdict(self, response: httpx.Response) -> Outcome:
        status = response.status_code
        if status == 404:
            return absent(response, SOURCE)
        if status == 403:
            # Тот же 403 приходит на нарушение пагинации в демо-режиме — эти
            # два случая не различить.
            return refuse_quota(self._http)
        if status == 401:
            return refuse_key()
        if status == 429:
            # В документации его нет, но это повод обработать, а не пропустить.
            return refuse_rate(self._http)
        if status != 200:
            return refuse_code(status)
        return self._answer(response)

    def _answer(self, response: httpx.Response) -> Outcome:
        return parsed(logger, SOURCE, "ответ основного зеркала не разобрался",
                      lambda: answered(parse_poiskkino(response.json())))

    async def aclose(self) -> None:
        await self._http.aclose()
