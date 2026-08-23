"""Разговор с Google Books по сети."""

import logging
from collections.abc import Callable
from datetime import date
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
from backend.sources.google_books.parse import (
    parse_by_author,
    parse_card,
    parse_search,
)
from backend.sources.http import SourceHttp

logger = logging.getLogger(__name__)

# Имя, которым источник подписывает свои отказы. Отдельной строкой, а не
# `self._http.name`: сторож `test_a_client_signs_refusals_with_the_name_it_calls_itself`
# сверяет подпись отказа с именем соединения, и возьми клиент имя оттуда же —
# сравнение выродилось бы в тавтологию. Ровно этим однажды обернулось общее
# `imdb` у двух оценочных клиентов.
SOURCE = "google_books"
BASE = "https://www.googleapis.com/books/v1/volumes"


class GoogleBooksClient:
    """Единственный источник книг.

    Листает: `startIndex` — это смещение буквально, и никакого перевода в
    страницы ему не нужно. Замерено: при `maxResults=20` первые строки порций
    0, 20 и 40 разные, пересечений нет.

    Довод `kind` есть ради общего контракта каталожных клиентов и игнорируется:
    книгами содержимое здесь и ограничено."""

    PAGES: ClassVar[bool] = True

    def __init__(self, http: SourceHttp, api_keys: tuple[str, ...]) -> None:
        self._http = http
        self._keys = api_keys
        # Номер ключа, которым спрашивают сейчас, и сутки, на которые он
        # исчерпан. Внутри суток номер двигается только вперёд: исчерпанный
        # ключ до полуночи не оживёт, и возвращаться к нему значит тратить на
        # `429` по походу в сеть с каждого запроса. В полночь оживает и он —
        # квота суточная, — а окно приложения живёт открытым сутками.
        self._at = 0
        self._day: date | None = None

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
        замерено, пять запросов из десяти.

        Исчерпанная квота — не отказ, пока есть запасной ключ: суточная тысяча
        считается на проект, и ключ от другого аккаунта продлевает день. Запрос
        повторяется тем же вызовом, а отказом `429` становится только у
        последнего ключа."""
        while True:
            self._forget_yesterday()
            asked_with = self._at
            response = await asked_until_free(
                self._http, url, {"key": self._key, **extra})
            if not isinstance(response, httpx.Response):
                return response
            if response.status_code == 429 and self._another_key(asked_with):
                continue
            verdict = self._verdict(response)
            if verdict is not None:
                return verdict
            return parsed(logger, SOURCE, complaint,
                          lambda: Found(parse(response.json())))

    @property
    def _key(self) -> str:
        """Ключ, которым спрашивают сейчас. Пустая строка, если не вписан ни
        один: ручка ответит `400`, и человек прочтёт «ключ не принят» — то же,
        что при негодном."""
        return self._keys[self._at] if self._at < len(self._keys) else ""

    def _another_key(self, asked_with: int) -> bool:
        """Есть ли чем повторить запрос, ответивший «квота кончилась».

        Сосед мог сдвинуть номер раньше нас: карточки грузятся разом, и на
        исчерпанной квоте `429` приходит сразу нескольким запросам. Тогда
        сдвигать нечего — запасной уже стоит, — а повторить надо им же.
        Сдвинь номер и здесь, и запрос перешагнул бы через запасной: у пары
        ключей он спросил бы пустой строкой и прочёл «ключ не принят». Откажи —
        и вышло бы хуже: отказ по квоте закрывает источник до полуночи, а
        значит и повтор соседа получил бы «предохранитель взведён»."""
        if asked_with != self._at:
            return True
        if self._at + 1 >= len(self._keys):
            return False
        self._at += 1
        logger.info("%s: суточная квота ключа исчерпана, беру запасной", SOURCE)
        return True

    def _forget_yesterday(self) -> None:
        """Новые сутки — снова с первого ключа: суточная квота у него сброшена
        вместе с квотой последнего.

        Сутки считаются теми же часами, что и срок предохранителя (`clock` у
        соединения, местное время): своих у ключа быть не должно — иначе
        источник открылся бы раньше, чем оживает ключ, или наоборот."""
        today = self._http.clock().date()
        if today != self._day:
            self._at, self._day = 0, today

    async def search(self, query: str, kind: Kind, offset: int = 0) -> Outcome:
        """Выдача по строке, порцией и со смещения.

        Порция общая, `SEARCH_SIZE`, и довод к ней записан у самого объявления.
        Здесь остаётся то, чего там знать не могут: **в предел ручки двадцать
        укладывается** — умолчание у неё десять, предел сорок, на сорок первой
        приходит `400`. Замерено 22.08.2026."""
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
        GOG, у которых идентичности нет вовсе."""
        return Found([PersonHit(source_id=name)])

    async def credits_of(self, person_id: str, kind: Kind) -> Outcome:
        """Книги автора. `person_id` здесь — его имя (см. `find_people`), и
        спрашивается он оператором `inauthor:` обычной выдачей.

        Тёзки и разночтения приезжают вместе с точным написанием — замерено, по
        «Frank Herbert» в двадцати строках стоят и `FRANK. HERBERT`, и
        `Brian Herbert`. Отбора среди найденных снаружи людей нет: правило от
        31.07.2026, общее для всех источников.

        Порции у этого жеста нет: следующей страницы за кликом по имени не
        бывает, и просится он одной порцией — той же, что и строка поиска."""
        return await self._taken(
            BASE, f"книги автора {person_id} не разобрались",
            lambda payload: parse_by_author(payload, person_id),
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
