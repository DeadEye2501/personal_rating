"""Разговор с TMDB по сети."""

import logging

import httpx

from backend.model import Kind
from backend.sources.errors import Found, Outcome, Reason, Refusal
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

BROKEN_BY_PARSING = (ValueError, TypeError, KeyError, AttributeError)


class TmdbClient:
    # У сериала credits отдаёт последний сезон — один актёр вместо трёхсот.
    _APPEND = {
        Kind.MOVIE: "credits",
        Kind.SERIES: "aggregate_credits,external_ids",
    }

    def __init__(self, http: SourceHttp, api_key: str) -> None:
        self._http = http
        self._key = api_key

    def _params(self, **extra: object) -> dict:
        return {"api_key": self._key, "language": LANGUAGE, **extra}

    async def search(self, query: str, kind: Kind) -> Outcome:
        path = "/search/tv" if kind is Kind.SERIES else "/search/movie"
        response = await self._http.get(
            f"{BASE}{path}", params=self._params(query=query)
        )
        if not isinstance(response, httpx.Response):
            return response
        try:
            return Found(parse_search(response.json(), kind))
        except BROKEN_BY_PARSING as error:
            logger.warning("tmdb: выдача поиска не разобралась — %s", error)
            return Refusal(source="tmdb", reason=Reason.BROKEN, detail=str(error))

    async def card(self, source_id: str, kind: Kind) -> Outcome:
        path = "tv" if kind is Kind.SERIES else "movie"
        response = await self._http.get(
            f"{BASE}/{path}/{source_id}",
            params=self._params(append_to_response=self._APPEND[kind]),
        )
        if not isinstance(response, httpx.Response):
            return response

        parse = parse_series if kind is Kind.SERIES else parse_movie
        try:
            return Found(parse(response.json()))
        except (Incomplete, *BROKEN_BY_PARSING) as error:
            logger.warning("tmdb: карточка %s не разобралась — %s", source_id, error)
            return Refusal(source="tmdb", reason=Reason.BROKEN, detail=str(error))

    async def aclose(self) -> None:
        await self._http.aclose()
