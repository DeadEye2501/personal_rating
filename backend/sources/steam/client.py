"""Разговор со Steam по сети."""

import json
import logging
from dataclasses import replace
from urllib.parse import quote

import httpx

from backend.model import (
    Found,
    GenreSource,
    Kind,
    Missing,
    Outcome,
    Reason,
    Refusal,
    SearchHit,
)
from backend.sources.errors import BROKEN_BY_PARSING, broken, parsed, parsed_or
from backend.sources.http import SourceHttp
from backend.sources.undocumented import asked
from backend.sources.steam.parse import (
    released_in,
    cover_of,
    parse_card,
    parse_search,
    parse_tags,
    sifted,
)

logger = logging.getLogger(__name__)

SEARCH = "https://steamcommunity.com/actions/SearchApps"
DETAILS = "https://store.steampowered.com/api/appdetails"
# Ни тегов, ни рода товара, ни настоящего имени файла обложки в `appdetails`
# нет — всё это живёт здесь.
ITEMS = "https://api.steampowered.com/IStoreBrowseService/GetItems/v1/"

# `country_code: RU` отдаёт `success: 15`, `visible: false` и ответ без рода
# товара — на живую игру, а не на несуществующую. Проверено 03.08.2026. Нужен US.
ITEMS_CONTEXT = {"language": "russian", "country_code": "US", "steam_realm": 1}
# Выдаче нужен род товара, адрес обложки и год выхода; карточке — то же и теги.
# Год выдаче нужен для склейки: годы, разошедшиеся больше чем на люфт, означают
# разные игры. Стоит он ноль — замерено 03.08.2026: +560 байт на 13 КБ и то же
# время, потому что запрос выдача делает всё равно.
SIFT_WANTED = {"include_assets": True, "include_release": True}
CARD_WANTED = SIFT_WANTED | {"include_tag_count": 20}


class SteamClient:
    """Аргумент `kind` есть ради общего контракта каталожных клиентов и
    игнорируется: у Steam содержимое одного типа."""

    def __init__(self, http: SourceHttp) -> None:
        self._http = http

    @property
    def name(self) -> str:
        """Под этим именем источник назовётся в отказе — в том числе в отказе,
        который соберёт не он сам, а поймавший его исключение сервис."""
        return self._http.name

    async def search(self, query: str, kind: Kind) -> Outcome:
        # Строка поиска идёт частью пути, поэтому её надо экранировать: `?` и
        # `#` для URL структурные, и «Who's Your Daddy?!» уедет обрезанным до
        # «Who's Your Daddy». Steam при этом ответит 200 и найдёт не то, что
        # просили, — то есть тихо неверная выдача, а не отказ.
        answer = await asked(self._http, f"{SEARCH}/{quote(query, safe='')}")
        if not isinstance(answer, httpx.Response):
            return answer
        hits = parsed(logger, "steam", "выдача поиска не разобралась",
                      lambda: parse_search(answer.json()))
        if isinstance(hits, Refusal):
            return hits
        return Found(await self._narrowed(hits))

    async def _narrowed(self, hits: list[SearchHit]) -> list[SearchHit]:
        """Дополнения, инструменты и playtest-ы убираются до показа, а не после:
        показанная строка заводится в базу сама, и мелькнувшая успела бы. Тем же
        ответом приезжает настоящий адрес вертикальной обложки.

        Не ответили — отдаём выдачу как есть: потерять настоящую игру хуже, чем
        показать лишнее дополнение."""
        if not hits:
            return hits
        payload = await self._items([hit.source_id for hit in hits], SIFT_WANTED)
        if payload is None:
            return hits
        return parsed_or(logger, "steam", "род товара не разобрался",
                         lambda: sifted(hits, payload), hits)

    async def card(self, source_id: str, kind: Kind) -> Outcome:
        # Отсутствия Steam кодом не выражает: битый или отсутствующий appids
        # даёт 400 и тело `null`, поэтому «такого нет» читается ниже, из тела.
        # Регион обязателен: без него `appdetails` отвечает `success: false` про
        # живую игру — замерено на `Fallout: New Vegas` 03.08.2026, с `cc=us`
        # приезжает полная карточка. Ту же ловушку обходит `ITEMS_CONTEXT`.
        answer = await asked(self._http, DETAILS,
                             {"appids": source_id, "l": "russian", "cc": "us"})
        if not isinstance(answer, httpx.Response):
            return answer

        try:
            payload = answer.json()
            block = payload.get(source_id)
            if block is None:
                # Ответ про другую игру. Молча подставить его — значит записать
                # чужую карточку под видом запрошенной.
                logger.warning(
                    "steam: ответ не про %s, а про %s", source_id, list(payload)
                )
                return Refusal(
                    source="steam",
                    reason=Reason.BROKEN,
                    detail="ответ про другой appid",
                )
            if not block.get("success"):
                # Ответ, а не отказ: не различает «нет» и «скрыта из витрины».
                return Missing()
            card = parse_card(block["data"])
        except BROKEN_BY_PARSING as error:
            logger.warning("steam: карточка %s не разобралась — %s", source_id, error)
            return broken("steam", error)

        # Уточнения добираются вне общего `try`: карточка уже собрана и годится,
        # и уронить её из-за них было бы обменом целого на украшение.
        tags, cover, year = await self._beyond_details(source_id)
        item = replace(card.item, poster_url=cover) if cover else card.item
        item = replace(item, year=year) if year else item
        return Found(replace(card, item=item,
                             genre_ext_ids=card.genre_ext_ids + tags))

    async def _items(self, appids: list[str], wanted: dict) -> dict | None:
        """Ответ `GetItems` на список appid. Ручкой пользуются двое — карточка и
        выдача, — и различаются они только тем, что просят и что читают.

        Отказ здесь ничего не роняет, поэтому наружу идёт `None`, а не
        `Refusal`: обоим потребителям есть чем обойтись.

        Идёт мимо `asked()` намеренно: неописанный код ответа не должен глушить
        Steam на пять минут из-за уточнения к уже собранному. Сетевой сбой при
        этом предохранитель взводит, как везде, — его ставит сам `SourceHttp`, и
        пустая сеть остаётся бедой всех следующих запросов, а не одного."""
        # Нечисловой appid не спрашивается вовсе: `int()` вокруг сборки запроса
        # потребовал бы своего `except`, а результат тот же — Steam про такую
        # строку не ответит, и она останется в выдаче как неспрошенная.
        request = json.dumps({
            "ids": [{"appid": int(one)} for one in appids if one.isdigit()],
            "context": ITEMS_CONTEXT,
            "data_request": wanted,
        })
        response = await self._http.get(ITEMS, params={"input_json": request})
        if not isinstance(response, httpx.Response):
            return None
        if response.status_code != 200:
            logger.warning("steam: GetItems про %s не приехал, код %s",
                           appids, response.status_code)
            return None
        return parsed_or(logger, "steam", f"ответ GetItems про {appids} не разобрался",
                         response.json, None)

    async def _beyond_details(
        self, source_id: str
    ) -> tuple[tuple[tuple[GenreSource, str], ...], str, int | None]:
        """Теги, настоящий адрес обложки и год выхода: `appdetails` первых двух
        не знает вовсе, а третий отдаёт магазинный — у `Fallout` 2015 вместо
        1997. Живут они в одном ответе, значит и запрос один.

        Отказ карточку не роняет. Без тегов она беднее: своих жанров у Steam
        двенадцать на весь магазин. Без адреса — остаётся угаданный, и он верен
        в 62% случаев."""
        payload = await self._items([source_id], CARD_WANTED)
        if payload is None:
            return (), "", None
        tags = parsed_or(logger, "steam", f"теги {source_id} не разобрались",
                         lambda: parse_tags(payload, source_id), ())
        cover = parsed_or(logger, "steam", f"обложка {source_id} не разобралась",
                          lambda: cover_of(payload, source_id), "")
        year = parsed_or(logger, "steam", f"год {source_id} не разобрался",
                         lambda: released_in(payload, source_id), None)
        return tags, cover, year

    async def aclose(self) -> None:
        await self._http.aclose()
