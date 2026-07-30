"""Разговор с GOG по сети."""

import logging

import httpx

from backend.model import Found, Kind, Missing, Outcome, Reason, Refusal
from backend.sources.errors import parsed
from backend.sources.gog.parse import find_slug, parse_catalog, to_hit
from backend.sources.http import SourceHttp
from backend.sources.undocumented import refuse_undocumented

logger = logging.getLogger(__name__)

CATALOG = "https://catalog.gog.com/v1/catalog"


class GogClient:
    """Поиск GOG никогда не отвечает «не найдено»: на бессмыслицу приезжает
    200 и два десятка несвязанных игр, на пустой запрос — весь каталог.

    Отсюда правило, которое этот клиент обязан держать: **`Missing` не
    возвращается ни из `search`, ни из `card`.** Пустой список — это «поиск
    отранжировал мимо», а не «игры в каталоге нет».

    Аргумент `kind` есть ради общего контракта каталожных клиентов и
    игнорируется: у GOG содержимое одного типа."""

    def __init__(self, http: SourceHttp) -> None:
        self._http = http

    @property
    def name(self) -> str:
        """Под этим именем источник назовётся в отказе — в том числе в отказе,
        который соберёт не он сам, а поймавший его исключение сервис."""
        return self._http.name

    async def _payload(self, query: str) -> dict | Refusal:
        """Тело ответа каталога. Разбирают его двое и по-разному: поиску нужны
        кандидаты, привязке — номер по слагу."""
        response = await self._http.get(
            CATALOG, params={"query": f"like:{query}", "locale": "ru-RU"}
        )
        if not isinstance(response, httpx.Response):
            return response
        if response.status_code != 200:
            return refuse_undocumented(self._http, response.status_code)
        return parsed(logger, "gog", "тело каталога не разобралось",
                      response.json)

    async def _catalog(self, query: str) -> list | Refusal:
        payload = await self._payload(query)
        if isinstance(payload, Refusal):
            return payload
        return parsed(logger, "gog", "каталог не разобрался",
                      lambda: parse_catalog(payload))

    async def search(self, query: str, kind: Kind) -> Outcome:
        cards = await self._catalog(query)
        if isinstance(cards, Refusal):
            return cards
        return Found([to_hit(card) for card in cards])

    async def card(self, source_id: str, kind: Kind) -> Outcome:
        """Повторяет тот же запрос и выбирает нужный идентификатор. Лишний
        запрос — цена за то, что контракт у трёх магазинов один.

        Не нашли нужный id — это «поиск отранжировал мимо», а не «игры в
        каталоге нет»: спрашиваем мы конкретный идентификатор, но спрашиваем
        его у поиска по названию."""
        cards = await self._catalog(source_id)
        if isinstance(cards, Refusal):
            return cards
        for card in cards:
            if card.item.source_id == source_id:
                return Found(card)
        return Refusal(
            source="gog",
            reason=Reason.BROKEN,
            detail=f"каталог не вернул {source_id}",
        )

    async def resolve_slug(self, slug: str) -> Outcome:
        """В адресе у GOG слаг, а каталогу нужен номер. Спрашиваем каталог тем же
        слагом, разобранным на слова, и берём только точное совпадение.

        `Missing` тут возвращается, хотя из `search` и `card` — никогда: здесь
        спрашивают не «что похоже на это название», а «есть ли ровно такой
        слаг», и его отсутствие — честный ответ."""
        payload = await self._payload(slug.replace("_", " "))
        if isinstance(payload, Refusal):
            return payload
        found = parsed(logger, "gog", f"каталог по слагу {slug} не разобрался",
                       lambda: find_slug(payload, slug))
        if isinstance(found, Refusal):
            return found

        if found is None:
            logger.info("gog: слага %s в каталоге не нашлось", slug)
            return Missing()
        return Found(found)

    async def aclose(self) -> None:
        await self._http.aclose()
