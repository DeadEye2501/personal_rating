"""Разговор с TMDB по сети."""

import logging
from collections.abc import Callable
from datetime import timedelta
from typing import ClassVar

import httpx

from backend.model import (
    SEARCH_SIZE,
    Found,
    Kind,
    Missing,
    Outcome,
    Reason,
    Refusal,
)
from backend.sources.backoff import refuse_until
from backend.sources.errors import parsed
from backend.sources.http import SourceHttp
from backend.sources.tmdb.parse import (
    parse_credits,
    parse_movie,
    parse_people,
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
    # Листает: `page`, и `total_pages` у него правдив. Порция — ровно двадцать
    # строк, то есть страница и есть порция выдачи.
    PAGES: ClassVar[bool] = True

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
        называться один раз — тем же вызовом, что закрывает источник. Сама
        `classify` этого сделать не может: она разбирает ответ, а транспорта — и
        предохранителя вместе с ним — у неё нет."""
        verdict = classify(response)
        if isinstance(verdict, Refusal) and verdict.reason is Reason.RATE:
            return refuse_until(self._http, Reason.RATE, RATE_BACKOFF)
        return verdict

    async def _asked(self, url: str,
                     **extra: object) -> httpx.Response | Missing | Refusal:
        """Ответ, годный к разбору, — либо исход, который уже всё решил.

        Отделено от разбора, а не слито с ним: отказ на обрыв и на взведённый
        предохранитель собирает транспорт, отказ по чужому коду — `_verdict`, и
        после любого из них разбирать нечего. Зовёт это `_taken`, и он же
        единственный вызывающий: число ручек названо у него."""
        response = await self._http.get(url, params=self._params(**extra))
        if not isinstance(response, httpx.Response):
            return response
        verdict = self._verdict(response)
        return response if verdict is None else verdict

    async def _taken(self, url: str, complaint: str,
                     parse: Callable[[dict], object], **extra: object) -> Outcome:
        """Разобранное тело — либо исход, который уже всё решил.

        Пять ручек клиента отличаются адресом, параметрами, разборщиком и
        фразой в логе; хвост «ответ или готовый исход → разобрать» у них один и
        тот же."""
        answer = await self._asked(url, **extra)
        if not isinstance(answer, httpx.Response):
            return answer
        return parsed(logger, "tmdb", complaint,
                      lambda: Found(parse(answer.json())))

    async def search(self, query: str, kind: Kind, offset: int = 0) -> Outcome:
        """Смещение переводится в номер страницы здесь: у ручки TMDB порции
        считаются страницами, а идиома проекта — `limit`/`offset`, и разнобой на
        границе стоил бы того, что каждый зовущий помнил бы, кто из пяти
        клиентов какими единицами меряет."""
        path = "/search/tv" if kind is Kind.SERIES else "/search/movie"
        return await self._taken(
            f"{BASE}{path}", "выдача поиска не разобралась",
            lambda payload: parse_search(payload, kind), query=query,
            page=offset // SEARCH_SIZE + 1)

    async def credits_of(self, person_id: str, kind: Kind) -> Outcome:
        """Всё, что человек сделал, одним запросом.

        Порций у фильмографии нет: замерено, у самого плодовитого режиссёра 78
        строк съёмочной группы и 33 актёрских — меньше двух страниц выдачи."""
        path = "tv_credits" if kind is Kind.SERIES else "movie_credits"
        return await self._taken(
            f"{BASE}/person/{person_id}/{path}",
            f"фильмография {person_id} не разобралась",
            lambda payload: parse_credits(payload, kind))

    async def find_people(self, name: str) -> Outcome:
        """Для того, у кого внешней идентичности нет. Найденные приезжают все —
        это и есть ответ, и решение проекта прямо принимает их появление."""
        return await self._taken(f"{BASE}/search/person",
                                 "поиск человека не разобрался",
                                 parse_people, query=name)

    async def card(self, source_id: str, kind: Kind) -> Outcome:
        path = "tv" if kind is Kind.SERIES else "movie"
        parse = parse_series if kind is Kind.SERIES else parse_movie
        return await self._taken(f"{BASE}/{path}/{source_id}",
                                 f"карточка {source_id} не разобралась", parse,
                                 append_to_response=self._APPEND[kind])

    async def series_counts(self, source_id: str) -> Outcome:
        """Перезапрос по сроку. Без `append_to_response`: `aggregate_credits`
        тянет 167 КБ, а нужны два числа."""
        return await self._taken(f"{BASE}/tv/{source_id}",
                                 f"сезоны {source_id} не разобрались",
                                 parse_series_counts)

    async def aclose(self) -> None:
        await self._http.aclose()
