"""Разговор с Google Books по сети."""

import logging
from collections.abc import Callable
from typing import ClassVar

import httpx

from backend.model import (
    SEARCH_SIZE,
    Found,
    Kind,
    Missing,
    Outcome,
    PersonHit,
    Reason,
    Refusal,
)
from backend.sources.backoff import daily_quota
from backend.sources.busy import asked_until_free
from backend.sources.errors import absent, parsed, refuse_code
from backend.sources.google_books.parse import parse_card, parse_search
from backend.sources.http import SourceHttp

logger = logging.getLogger(__name__)

# Имя, которым источник подписывает свои отказы. Отдельной строкой, а не
# `self._http.name`: сторож `test_a_client_signs_refusals_with_the_name_it_calls_itself`
# сверяет подпись отказа с именем соединения, и возьми клиент имя оттуда же —
# сравнение выродилось бы в тавтологию. Ровно этим однажды обернулось общее
# `imdb` у двух оценочных клиентов.
SOURCE = "google_books"
BASE = "https://www.googleapis.com/books/v1/volumes"

# Сколько строк просить у выдачи — та же порция, которой меряет весь поиск.
# Своего числа здесь не заводится: по нему считают ещё в трёх местах — признак
# «есть ещё», шаг смещения в мосте и срез порции, — и разъехавшись, оно молчало
# бы в обе стороны. Меньше общей порции — признак «есть ещё» не встал бы
# никогда, больше — лишние строки срезались бы и приезжали вторым запросом из
# суточной тысячи.
#
# Умолчание ручки — десять строк, предел — сорок, на сорок первой приходит
# `400`. Замерено 22.08.2026, то есть двадцать в этот предел укладывается.


class GoogleBooksClient:
    """Единственный источник книг.

    Листает: `startIndex` — это смещение буквально, и никакого перевода в
    страницы ему не нужно. Замерено: при `maxResults=20` первые строки порций
    0, 20 и 40 разные, пересечений нет.

    Довод `kind` есть ради общего контракта каталожных клиентов и игнорируется:
    книгами содержимое здесь и ограничено."""

    PAGES: ClassVar[bool] = True

    def __init__(self, http: SourceHttp, api_key: str) -> None:
        self._http = http
        self._key = api_key

    @property
    def name(self) -> str:
        """Под этим именем источник назовётся в отказе — в том числе в отказе,
        который соберёт не он сам, а поймавший его исключение сервис."""
        return self._http.name

    def _verdict(self, response: httpx.Response) -> Missing | Refusal | None:
        """`None` — ответ успешный, разбирать дальше.

        Три кода означают три разных беды, и замерены все три: `404` с
        разобранным телом — «такого тома нет», `429` — исчерпанная суточная
        квота, `400` — негодный ключ. Смешай последние два, и битый ключ закрыл
        бы источник до полуночи, а человек прочёл бы «кончилась квота» там, где
        надо вписать другой ключ.

        Предохранитель по ключу не взводится: битый ключ сроком не лечится, и
        закрыв источник на сутки, мы не дали бы человеку вписать новый."""
        if response.status_code == 200:
            return None
        if response.status_code == 404:
            return absent(response, SOURCE)
        if response.status_code == 429:
            return daily_quota(self._http)
        if response.status_code == 400:
            return Refusal(source=SOURCE, reason=Reason.KEY,
                           detail="ключ не принят")
        return refuse_code(SOURCE, response.status_code)

    async def _taken(self, url: str, complaint: str,
                     parse: Callable[[dict], object], **extra: object) -> Outcome:
        """Разобранное тело — либо исход, который уже всё решил.

        Занятость перепрашивается до разбора: `503` у Google означает «занят
        сейчас», и принять его за пустую выдачу значит потерять половину книг —
        замерено, пять запросов из десяти."""
        response = await asked_until_free(
            self._http, url, {"key": self._key, **extra})
        if not isinstance(response, httpx.Response):
            return response
        verdict = self._verdict(response)
        if verdict is not None:
            return verdict
        return parsed(logger, SOURCE, complaint,
                      lambda: Found(parse(response.json())))

    async def search(self, query: str, kind: Kind, offset: int = 0) -> Outcome:
        return await self._taken(BASE, "выдача поиска не разобралась",
                                 parse_search, q=query, maxResults=SEARCH_SIZE,
                                 startIndex=offset)

    async def find_people(self, name: str) -> Outcome:
        """Идентичность автора у Google равна его имени.

        Своей ручки людей у источника нет вовсе: `authors` в ответе — голые
        строки, и `/search/person` ему не из чего собрать. Отсюда единственная
        строка в ответе и ни одного запроса: отбирать среди авторов нечего, а
        `credits_of` спросит этим же именем.

        Тёзки от этого не склеиваются больше, чем склеены: одноимённые авторы у
        Google неразличимы в самом источнике — та же цена, что у студий Steam и
        GOG, которых склеивают по имени с самого начала."""
        return Found([PersonHit(source_id=name)])

    async def credits_of(self, person_id: str, kind: Kind) -> Outcome:
        """Книги автора. `person_id` здесь — его имя (см. `find_people`), и
        спрашивается он оператором `inauthor:` обычной выдачей.

        Тёзки и разночтения приезжают вместе с точным написанием — замерено, по
        «Frank Herbert» в двадцати строках стоят и `FRANK. HERBERT`, и
        `Brian Herbert`. Отбора среди найденных снаружи людей нет: правило от
        31.07.2026, общее для всех источников."""
        return await self._taken(
            BASE, f"книги автора {person_id} не разобрались", parse_search,
            q=f'inauthor:"{person_id}"', maxResults=SEARCH_SIZE)

    async def card(self, source_id: str, kind: Kind) -> Outcome:
        """Карточка тома идёт своей ручкой, потому что полный путь BISAC есть
        только у неё: выдача обрезает его до верхушки и на «Задаче трёх тел»
        говорит `Fiction`, а карточка — `Fiction / Science Fiction / Hard
        Science Fiction`."""
        return await self._taken(f"{BASE}/{source_id}",
                                 f"карточка {source_id} не разобралась",
                                 parse_card)

    async def aclose(self) -> None:
        await self._http.aclose()
