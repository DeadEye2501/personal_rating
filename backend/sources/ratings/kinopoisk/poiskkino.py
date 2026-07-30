"""Основное зеркало Кинопоиска."""

import logging

import httpx

from backend.model import Kind
from backend.sources.errors import (
    Missing,
    Outcome,
    Reason,
    Refusal,
    parsed,
)
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
            return self._absent(response)
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

    def _absent(self, response: httpx.Response) -> Outcome:
        """Отрицательный факт — только по разобранному телу. Перед Кинопоиском
        стоит Envoy, и при падении апстрима он отдаёт свой 404 обычным текстом.
        Записать такую страницу как «Кинопоиск не знает этот фильм» значит
        поселить в базе ложь на неделю."""
        try:
            response.json()
        except ValueError:
            return Refusal(
                source=SOURCE,
                reason=Reason.BROKEN,
                detail="404 без JSON — это не «фильма нет»",
            )
        return Missing()

    def _answer(self, response: httpx.Response) -> Outcome:
        return parsed(logger, SOURCE, "ответ основного зеркала не разобрался",
                      lambda: answered(parse_poiskkino(response.json())))

    async def aclose(self) -> None:
        await self._http.aclose()
