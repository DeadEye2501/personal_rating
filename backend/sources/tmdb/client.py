"""Разговор с TMDB по сети."""

import logging

import httpx

from backend.model import Kind
from backend.sources.errors import Found, Outcome, Reason, Refusal
from backend.sources.http import SourceHttp
from backend.sources.tmdb.parse import parse_search

logger = logging.getLogger(__name__)

BASE = "https://api.themoviedb.org/3"
LANGUAGE = "ru-RU"


class TmdbClient:
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
        except (ValueError, TypeError, KeyError, AttributeError) as error:
            logger.warning("tmdb: выдача поиска не разобралась — %s", error)
            return Refusal(source="tmdb", reason=Reason.BROKEN, detail=str(error))

    async def aclose(self) -> None:
        await self._http.aclose()
