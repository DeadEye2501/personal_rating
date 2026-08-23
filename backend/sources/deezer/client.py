"""Разговор с Deezer по сети."""

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
from backend.sources.deezer.parse import parse_albums, parse_artists, parse_card
from backend.sources.errors import parsed, refuse_code
from backend.sources.http import SourceHttp

logger = logging.getLogger(__name__)

SOURCE = "deezer"
BASE = "https://api.deezer.com"

# Откат по частоте. Замерено 22.08.2026: 120 запросов подряд за 16.5 с проходят
# целиком, а срывается только залп одновременных — то есть Deezer отпускает за
# секунды. Минута берётся с запасом и покрывает его же объявленный предел в
# «50 запросов за 5 секунд».
RATE_BACKOFF = timedelta(minutes=1)

# Что означают коды в теле успешного ответа. Замерено: `4` — «слишком часто»,
# `800` — «такого у меня нет». Незнакомый код за отсутствие не принимается:
# отрицательный факт живёт неделю, и чужая беда, записанная им, стёрла бы
# альбом из выдачи на всё это время.
BUSY = 4
ABSENT = 800

# Сколько альбомов просить у исполнителя. Порции у этого жеста нет вовсе — ни в
# бэкенде, ни на странице, — и обрезанный ответ был бы недостижим ничем: до
# лишних альбомов человек не добрался бы никаким жестом и следа бы не увидел.
#
# Умолчание ручки — 25 с `next`, замерено 23.08.2026: у Мадонны 25 из 72, у
# Элвиса 25 из 42. С этим числом приезжают все: 72 из 72 и 42 из 42, а `next`
# пропадает. Предел ручки на этом не заканчивается — `limit=1000` отвечает так
# же и без ошибки.
ALL_ALBUMS = 1000


class DeezerClient:
    """Единственный источник музыки. Ключа не требует вовсе — как Steam, GOG и
    old-games.ru.

    Отказ у него приходит **под успешным кодом**: волна из 240 запросов дала
    `HTTP 200` у всех, а у 177 в теле лежало `{"error": {"code": 4}}`. Отсюда
    правило клиента: тело разбирается до всякого вывода из кода. Тем же
    способом отличает отсутствие Steam — по полю `success` внутри `200`.

    Довод `kind` есть ради общего контракта каталожных клиентов и игнорируется:
    у Deezer содержимое одного типа."""

    # Листает: `index` — это смещение буквально. Замерено, первые строки порций
    # 0 и 5 разные; `total` при этом плавает между соседними запросами одного и
    # того же, и верить ему нельзя.
    PAGES: ClassVar[bool] = True

    def __init__(self, http: SourceHttp) -> None:
        self._http = http

    @property
    def name(self) -> str:
        """Под этим именем источник назовётся в отказе — в том числе в отказе,
        который соберёт не он сам, а поймавший его исключение сервис."""
        return self._http.name

    def _verdict(self, payload: dict) -> Missing | Refusal | None:
        """`None` — в теле нет отказа, разбирать дальше."""
        error = payload.get("error")
        if not error:
            return None
        if not isinstance(error, dict):
            # Форма ошибки у Deezer объявлена объектом, и все замеренные такие.
            # Придёт строкой — классифицировать нечем, а `error.get` уронил бы
            # `AttributeError` мимо обеих обёрток: в лог уехала бы трассировка
            # вместо названной жалобы.
            return Refusal(source=SOURCE, reason=Reason.BROKEN,
                           detail=f"ошибка не объект: {error}")
        code = error.get("code")
        if code == ABSENT:
            return Missing()
        if code == BUSY:
            return refuse_until(self._http, Reason.RATE, RATE_BACKOFF)
        return Refusal(source=SOURCE, reason=Reason.BROKEN,
                       detail=f"код ошибки {code}: {error.get('message')}")

    async def _taken(self, path: str, complaint: str,
                     parse: Callable[[dict], object], **params: object) -> Outcome:
        """Разобранное тело — либо исход, который уже всё решил.

        Порядок здесь и есть всё содержание клиента: сначала тело, потом код.
        Код проверяется после, а не вместо: у ответа без тела разбирать нечего,
        и молчаливая пустота вместо отказа означала бы «такого нет»."""
        response = await self._http.get(f"{BASE}{path}", params=params)
        if not isinstance(response, httpx.Response):
            return response

        payload = parsed(logger, SOURCE, "тело ответа не разобралось",
                         response.json)
        if isinstance(payload, Refusal):
            return payload
        if not isinstance(payload, dict):
            return Refusal(source=SOURCE, reason=Reason.BROKEN,
                           detail="тело не объект")

        verdict = self._verdict(payload)
        if verdict is not None:
            return verdict
        if response.status_code != 200:
            return refuse_code(SOURCE, response.status_code)
        return parsed(logger, SOURCE, complaint, lambda: Found(parse(payload)))

    async def search(self, query: str, kind: Kind, offset: int = 0) -> Outcome:
        return await self._taken("/search/album", "выдача поиска не разобралась",
                                 parse_albums, q=query, index=offset,
                                 limit=SEARCH_SIZE)

    async def card(self, source_id: str, kind: Kind) -> Outcome:
        """Карточка идёт своей ручкой: треки и полный список жанров есть только
        у неё — в строке выдачи лежит один жанр числом и ни одного трека."""
        return await self._taken(f"/album/{source_id}",
                                 f"карточка {source_id} не разобралась",
                                 parse_card)

    async def find_people(self, name: str) -> Outcome:
        """Найденные приезжают все — это и есть ответ на поиск по имени."""
        return await self._taken("/search/artist",
                                 "поиск исполнителя не разобрался",
                                 parse_artists, q=name)

    async def credits_of(self, person_id: str, kind: Kind) -> Outcome:
        """Всё, что исполнитель выпустил, одним запросом — как фильмография у
        TMDB. Идентичность у него настоящая, и спрашивать по имени значило бы
        притащить тёзок.

        Размер просится явно: без него ручка отдаёт 25 строк и `next`, а
        второй порции у этого жеста не бывает."""
        return await self._taken(f"/artist/{person_id}/albums",
                                 f"альбомы {person_id} не разобрались",
                                 parse_albums, limit=ALL_ALBUMS)

    async def aclose(self) -> None:
        await self._http.aclose()
