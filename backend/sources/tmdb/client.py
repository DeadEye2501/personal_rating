"""Разговор с TMDB по сети."""

import logging
from datetime import timedelta

import httpx

from backend.model import Found, Kind, Missing, Outcome, Reason, Refusal
from backend.sources.backoff import refuse_until
from backend.sources.errors import parsed
from backend.sources.http import SourceHttp
from backend.sources.tmdb.parse import (
    parse_movie,
    parse_search,
    parse_series,
    parse_series_counts,
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
        # Срок здесь не называется: его поставит `_verdict` тем же вызовом,
        # которым закроет источник, — иначе одно и то же число живёт в двух
        # местах, и разъехаться им ничто не мешает.
        return Refusal(source="tmdb", reason=Reason.RATE)
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
        следующий показ ленты упрётся в тот же 429.

        Отказ по частоте пересобирается, а не пропускается насквозь: срок должен
        называться один раз — тем же вызовом, что закрывает источник. У
        `classify` транспорта нет и быть не может, её зовут и без клиента."""
        verdict = classify(response)
        if isinstance(verdict, Refusal) and verdict.reason is Reason.RATE:
            return refuse_until(self._http, Reason.RATE, RATE_BACKOFF)
        return verdict

    async def _asked(self, url: str,
                     **extra: object) -> httpx.Response | Missing | Refusal:
        """Ответ, годный к разбору, — либо исход, который уже всё решил.

        Три запроса клиента отличаются только адресом и параметрами: отказ на
        обрыв и на взведённый предохранитель собирает транспорт, отказ по чужому
        коду — `_verdict`, и разбирать после любого из них нечего."""
        response = await self._http.get(url, params=self._params(**extra))
        if not isinstance(response, httpx.Response):
            return response
        verdict = self._verdict(response)
        return response if verdict is None else verdict

    async def search(self, query: str, kind: Kind) -> Outcome:
        path = "/search/tv" if kind is Kind.SERIES else "/search/movie"
        answer = await self._asked(f"{BASE}{path}", query=query)
        if not isinstance(answer, httpx.Response):
            return answer
        return parsed(logger, "tmdb", "выдача поиска не разобралась",
                      lambda: Found(parse_search(answer.json(), kind)))

    async def card(self, source_id: str, kind: Kind) -> Outcome:
        path = "tv" if kind is Kind.SERIES else "movie"
        answer = await self._asked(f"{BASE}/{path}/{source_id}",
                                   append_to_response=self._APPEND[kind])
        if not isinstance(answer, httpx.Response):
            return answer

        parse = parse_series if kind is Kind.SERIES else parse_movie
        return parsed(logger, "tmdb", f"карточка {source_id} не разобралась",
                      lambda: Found(parse(answer.json())))

    async def series_counts(self, source_id: str) -> Outcome:
        """Перезапрос по сроку. Без `append_to_response`: `aggregate_credits`
        тянет 167 КБ, а нужны два числа."""
        answer = await self._asked(f"{BASE}/tv/{source_id}")
        if not isinstance(answer, httpx.Response):
            return answer
        return parsed(logger, "tmdb", f"сезоны {source_id} не разобрались",
                      lambda: Found(parse_series_counts(answer.json())))

    async def aclose(self) -> None:
        await self._http.aclose()
