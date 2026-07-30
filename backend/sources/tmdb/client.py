"""Разговор с TMDB по сети."""

import logging
from datetime import timedelta

import httpx

from backend.model import Kind
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
from backend.sources.tmdb.parse import (
    Incomplete,
    parse_movie,
    parse_search,
    parse_series,
)

logger = logging.getLogger(__name__)

BASE = "https://api.themoviedb.org/3"
LANGUAGE = "ru-RU"

# Суточной квоты у TMDB нет, `Retry-After` он не отдаёт — откат свой.
RATE_BACKOFF = timedelta(minutes=1)

# Объекта нет: 34 — не найдено, 6 — битый идентификатор.
_ABSENT = {6, 34}


def classify(response: httpx.Response) -> Missing | Refusal | None:
    """`None` — ответ успешный, разбирать дальше."""
    if response.status_code == 200:
        return None

    try:
        status = response.json().get("status_code")
    except (ValueError, AttributeError):
        status = None

    # Отрицательный факт — только по разобранному телу с известным кодом:
    # страница от прокси под 404 неделю выдавала бы себя за «такого нет».
    if response.status_code == 404 and status in _ABSENT:
        return Missing()
    if response.status_code == 429:
        return Refusal(source="tmdb", reason=Reason.RATE, retry_after=RATE_BACKOFF)
    if response.status_code == 401:
        return Refusal(source="tmdb", reason=Reason.KEY)
    return Refusal(source="tmdb", reason=Reason.BROKEN,
                   detail=f"HTTP {response.status_code}, status_code {status}")


class TmdbClient:
    # У сериала credits отдаёт последний сезон — один актёр вместо трёхсот.
    _APPEND = {
        Kind.MOVIE: "credits",
        Kind.SERIES: "aggregate_credits,external_ids",
    }

    def __init__(self, http: SourceHttp, api_key: str) -> None:
        self._http = http
        self._key = api_key

    @property
    def name(self) -> str:
        """Под этим именем источник назовётся в отказе — в том числе в отказе,
        который соберёт не он сам, а поймавший его исключение сервис."""
        return self._http.name

    def _params(self, **extra: object) -> dict:
        return {"api_key": self._key, "language": LANGUAGE, **extra}

    def _verdict(self, response: httpx.Response) -> Missing | Refusal | None:
        """Разобранный отказ, а заодно взведённый предохранитель: без него
        следующий показ ленты упрётся в тот же 429."""
        verdict = classify(response)
        if isinstance(verdict, Refusal) and verdict.reason is Reason.RATE:
            self._http.breaker.trip(RATE_BACKOFF, Reason.RATE)
        return verdict

    async def search(self, query: str, kind: Kind) -> Outcome:
        path = "/search/tv" if kind is Kind.SERIES else "/search/movie"
        response = await self._http.get(
            f"{BASE}{path}", params=self._params(query=query)
        )
        if not isinstance(response, httpx.Response):
            return response
        verdict = self._verdict(response)
        if verdict is not None:
            return verdict
        try:
            return Found(parse_search(response.json(), kind))
        except BROKEN_BY_PARSING as error:
            logger.warning("tmdb: выдача поиска не разобралась — %s", error)
            return broken("tmdb", error)

    async def card(self, source_id: str, kind: Kind) -> Outcome:
        path = "tv" if kind is Kind.SERIES else "movie"
        response = await self._http.get(
            f"{BASE}/{path}/{source_id}",
            params=self._params(append_to_response=self._APPEND[kind]),
        )
        if not isinstance(response, httpx.Response):
            return response
        verdict = self._verdict(response)
        if verdict is not None:
            return verdict

        parse = parse_series if kind is Kind.SERIES else parse_movie
        try:
            return Found(parse(response.json()))
        except (Incomplete, *BROKEN_BY_PARSING) as error:
            logger.warning("tmdb: карточка %s не разобралась — %s", source_id, error)
            return broken("tmdb", error)

    async def aclose(self) -> None:
        await self._http.aclose()
