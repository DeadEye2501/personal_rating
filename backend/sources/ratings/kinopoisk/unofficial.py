"""Запасное зеркало Кинопоиска."""

import logging
from collections.abc import Callable

import httpx

from backend.model import Found, Kind, Missing, Outcome, Ratings
from backend.sources.errors import parsed
from backend.sources.http import SourceHttp
from backend.sources.ratings.kinopoisk.mirror import (
    SOURCE,
    answered,
    refuse_code,
    refuse_key,
    refuse_quota,
    refuse_rate,
)
from backend.sources.ratings.kinopoisk.parse import (
    parse_unofficial,
    parse_unofficial_card,
)

logger = logging.getLogger(__name__)

# Именно /films, а не search-by-keyword: у второго 404 означает и «фильм не
# найден», и «поиск ничего не дал» — два разных смысла в одном коде.
BASE = "https://kinopoiskapiunofficial.tech/api/v2.2/films"


def _needs_the_card(ratings: Ratings) -> bool:
    """Фильм нашёлся, а оценки в списке нет. Спрашивать карточку по номеру есть
    смысл ровно тогда: без номера её не запросить, а с оценкой она не нужна."""
    return not ratings.values and bool(ratings.external_ids)


class UnofficialClient:
    def __init__(self, http: SourceHttp, api_key: str) -> None:
        self._http = http
        self._key = api_key

    async def ratings(self, imdb_id: str, kind: Kind) -> Outcome:
        response = await self._http.get(
            BASE,
            params={"imdbId": imdb_id},  # префикс tt обязателен
            headers={"X-API-KEY": self._key},
        )
        if not isinstance(response, httpx.Response):
            return response

        found = self._verdict(response, parse_unofficial)
        if isinstance(found, Found) and _needs_the_card(found.value):
            return await self._card(found.value)
        return found

    async def _card(self, listed: Ratings) -> Outcome:
        """Оценка из карточки по номеру: в списке её может не быть вовсе.

        Замерено живьём 02.08.2026 на «Гражданине-мстителе» — в списке
        `ratingKinopoisk: null`, в карточке `6.5`; у «Интерстеллара» она стоит и
        в списке, поэтому на нём этот случай не наблюдается. Второй запрос
        уходит только тут: у зеркала пятьсот запросов в сутки, и платить вторым
        за каждую карточку незачем.

        Ответ списка не выбрасывается: в нём уже приехал номер Кинопоиска, по
        которому на карточке зажигается ссылка на источник. Не оказалось оценки
        и в карточке — отдаём его, пустое значение тут законно и честно.

        А вот **отказ** карточки отдаётся отказом, и номер в этот раз пропадает:
        отдай мы вместо него ответ списка, обогащение записало бы «оценки нет»
        на неделю — ровно ту ошибку, ради которой второй запрос и заведён.
        Пропажа лечится сама: отказ не закрывает просрочку, и следующий показ
        карточки спросит снова."""
        response = await self._http.get(
            f"{BASE}/{listed.external_ids[0].value}",
            headers={"X-API-KEY": self._key},
        )
        if not isinstance(response, httpx.Response):
            return response

        card = self._verdict(response, parse_unofficial_card)
        if isinstance(card, Found) and card.value.values:
            return card
        return Found(listed) if isinstance(card, (Found, Missing)) else card

    def _verdict(self, response: httpx.Response,
                 parse: Callable[[dict], Ratings]) -> Outcome:
        status = response.status_code
        if status == 402:
            return refuse_quota(self._http)
        if status == 429:
            # Может прийти от nginx с телом text/html — JSON не разбираем.
            return refuse_rate(self._http)
        if status == 401:
            return refuse_key()
        if status != 200:
            return refuse_code(status)

        return parsed(logger, SOURCE, "ответ запасного зеркала не разобрался",
                      lambda: answered(parse(response.json())))

    async def aclose(self) -> None:
        await self._http.aclose()
