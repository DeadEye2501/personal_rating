"""Разговор со Steam по сети."""

import json
import logging
from dataclasses import replace
from urllib.parse import quote

import httpx

from backend.model import Found, GenreSource, Kind, Missing, Outcome, Reason, Refusal
from backend.sources.errors import BROKEN_BY_PARSING, broken, parsed
from backend.sources.http import SourceHttp
from backend.sources.undocumented import asked
from backend.sources.steam.parse import parse_card, parse_search, parse_tags

logger = logging.getLogger(__name__)

SEARCH = "https://steamcommunity.com/actions/SearchApps"
DETAILS = "https://store.steampowered.com/api/appdetails"
# Теги живут отдельно от карточки: в `appdetails` их нет вовсе.
TAGS = "https://api.steampowered.com/IStoreBrowseService/GetItems/v1/"

# `country_code: RU` отдаёт пустой ответ — `visible: false`,
# `unvailable_for_country_restriction: true`, проверено живьём. Нужен `US`.
TAGS_CONTEXT = {"language": "russian", "country_code": "US", "steam_realm": 1}
TAGS_WANTED = {"include_tag_count": 20}


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
        return parsed(logger, "steam", "выдача поиска не разобралась",
                      lambda: Found(parse_search(answer.json())))

    async def card(self, source_id: str, kind: Kind) -> Outcome:
        # Отсутствия Steam кодом не выражает: битый или отсутствующий appids
        # даёт 400 и тело `null`, поэтому «такого нет» читается ниже, из тела.
        answer = await asked(self._http, DETAILS,
                             {"appids": source_id, "l": "russian"})
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

        # Теги добираются вне общего `try`: карточка уже собрана и годится, и
        # уронить её из-за них было бы обменом целого на украшение.
        return Found(
            replace(
                card, genre_ext_ids=card.genre_ext_ids + await self._tags(source_id)
            )
        )

    async def _tags(self, source_id: str) -> tuple[tuple[GenreSource, str], ...]:
        """Теги отдельным запросом: в `appdetails` их нет вовсе.

        Отказ здесь карточку не роняет — жанров у Steam всего двенадцать на
        весь магазин, так что без тегов карточка беднее, а не сломана."""
        try:
            wanted = {
                "ids": [{"appid": int(source_id)}],
                "context": TAGS_CONTEXT,
                "data_request": TAGS_WANTED,
            }
            response = await self._http.get(
                TAGS, params={"input_json": json.dumps(wanted)}
            )
            if not isinstance(response, httpx.Response):
                return ()
            if response.status_code != 200:
                logger.warning(
                    "steam: теги %s не приехали, код %s",
                    source_id,
                    response.status_code,
                )
                return ()
            return parse_tags(response.json())
        except BROKEN_BY_PARSING as error:
            logger.warning("steam: теги %s не разобрались — %s", source_id, error)
            return ()

    async def aclose(self) -> None:
        await self._http.aclose()
