"""Разговор с old-games.ru по сети."""

import logging
from typing import ClassVar

import httpx

from backend.model import Found, Kind, Outcome, Refusal
from backend.sources.busy import asked_until_free
from backend.sources.errors import parsed
from backend.sources.http import SourceHttp
from backend.sources.oldgames.parse import parse_card, parse_search
from backend.sources.undocumented import refuse_undocumented

logger = logging.getLogger(__name__)

# Базовый адрес живёт здесь, а не в разборе: у шести остальных источников он
# тоже в клиенте, а разбору хватает того, что ему передали.
BASE = "https://www.old-games.ru"
CATALOG = f"{BASE}/catalog/"
CARD = BASE + "/game/{source_id}.html"


class OldGamesClient:
    """Единственный источник без API: отвечает страницами, а не JSON.

    `503` у него — штатный ответ на большой выдаче, и обходиться с ним как с
    отказом нельзя: утечёт он в предохранитель — источник будет замолкать после
    каждого поиска, и выглядеть это будет как «old-games работает через раз».

    Довод `kind` есть ради общего контракта каталожных клиентов и игнорируется:
    у сайта содержимое одного типа."""

    # Не листает: вся выдача приезжает одним запросом, второй порции у неё нет.
    PAGES: ClassVar[bool] = False

    def __init__(self, http: SourceHttp) -> None:
        self._http = http

    @property
    def name(self) -> str:
        return self._http.name

    async def _page(self, url: str, params: dict | None = None) -> str | Refusal:
        """Тело страницы — или отказ, который уже всё решил.

        Повтор при занятости общий, а классификация своя: у этого сайта не
        описан ни один код, и любой не-200 неизвестен ровно так же, как был бы
        неизвестен у магазина.

        Очередь к сайту держит `SourceHttp`, а не повтор: соединений к нему
        два — карточки идут своим, обложки своим, — и предел, поставленный
        здесь, накрыл бы только половину."""
        response = await asked_until_free(self._http, url, params)
        if not isinstance(response, httpx.Response):
            return response
        if response.status_code != 200:
            return refuse_undocumented(self._http, response.status_code)
        return response.text

    async def search(self, query: str, kind: Kind, offset: int = 0) -> Outcome:
        """Вся выдача одним запросом и сразу: порции у этого источника нет.

        Смещение принимается ради общего контракта и никуда не уезжает: просить
        его у сайта нечем, и со смещением сервис сюда не придёт — `PAGES` ложно.

        Строка выдачи несёт всё, кроме обложки, разработчика и описания, — их
        добирает карточка. У магазинов иначе: там обложка приезжает прямо в
        строке выдачи, и второго запроса ради неё не нужно."""
        page = await self._page(CATALOG, {"gamename": query})
        if isinstance(page, Refusal):
            return page
        return parsed(logger, "old_games", "выдача не разобралась",
                      lambda: Found(parse_search(page)))

    async def card(self, source_id: str, kind: Kind) -> Outcome:
        page = await self._page(CARD.format(source_id=source_id))
        if isinstance(page, Refusal):
            return page
        return parsed(logger, "old_games", f"карточка {source_id} не разобралась",
                      lambda: Found(parse_card(page, source_id)))

    async def aclose(self) -> None:
        await self._http.aclose()
