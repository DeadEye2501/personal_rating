"""Разговор с MDBList по сети."""

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
from backend.sources.ratings.mdblist.parse import parse_ratings

logger = logging.getLogger(__name__)

# Актуальный адрес. Легаси `mdblist.com/api` отдаёт 503 с телом, где битый ключ
# и исчерпанный лимит слиты в один ответ — различить их там нечем.
BASE = "https://api.mdblist.com"

QUOTA_FALLBACK = timedelta(hours=1)


def _retry_after(response: httpx.Response) -> timedelta | None:
    raw = response.headers.get("Retry-After")
    return timedelta(seconds=int(raw)) if raw and raw.isdigit() else None


class MdbListClient:
    def __init__(self, http: SourceHttp, api_key: str) -> None:
        self._http = http
        self._key = api_key

    async def ratings(self, imdb_id: str, kind: Kind) -> Outcome:
        media = "show" if kind is Kind.SERIES else "movie"
        response = await self._http.get(
            f"{BASE}/imdb/{media}/{imdb_id}", params={"apikey": self._key}
        )
        if not isinstance(response, httpx.Response):
            return response
        return self._verdict(response)

    def _verdict(self, response: httpx.Response) -> Outcome:
        status = response.status_code
        if status == 200:
            try:
                return Found(parse_ratings(response.json()))
            except BROKEN_BY_PARSING as error:
                logger.warning("mdblist: ответ не разобрался — %s", error)
                return broken("mdblist", error)
        if status == 404:
            return Missing()
        if status == 202:
            # Кеш строится — не отказ и не отсутствие, но писать нечего.
            return Refusal(
                source="mdblist",
                reason=Reason.RATE,
                retry_after=_retry_after(response),
            )
        if status == 429:
            delay = _retry_after(response) or QUOTA_FALLBACK
            self._http.breaker.trip(delay)
            return Refusal(source="mdblist", reason=Reason.QUOTA, retry_after=delay)
        if status in (401, 403):
            return self._denied(response)
        return Refusal(
            source="mdblist", reason=Reason.BROKEN, detail=f"HTTP {status}"
        )

    def _denied(self, response: httpx.Response) -> Refusal:
        """403 бывает и от Cloudflare с телом «error code: 1010» — тогда запрос
        до MDBList вообще не дошёл, и ключ тут ни при чём. Отличает их не код, а
        тело: у чужого периметра оно не JSON."""
        try:
            response.json()
        except ValueError:
            logger.warning("mdblist: чужой периметр — %s", response.text[:80])
            return Refusal(
                source="mdblist",
                reason=Reason.NETWORK,
                detail=response.text[:200],
            )
        return Refusal(
            source="mdblist", reason=Reason.KEY, detail=response.text[:200]
        )

    async def aclose(self) -> None:
        await self._http.aclose()
