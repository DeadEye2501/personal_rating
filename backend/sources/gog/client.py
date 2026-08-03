"""Разговор с GOG по сети."""

import logging
from dataclasses import replace

import httpx

from backend.model import Found, Kind, Missing, Outcome, Reason, Refusal
from backend.sources.errors import absent, parsed
from backend.sources.gog.parse import (
    find_slug,
    parse_catalog,
    parse_hits,
    title_of,
)
from backend.sources.http import SourceHttp
from backend.sources.undocumented import asked, refuse_undocumented
from backend.unique import unique

logger = logging.getLogger(__name__)

CATALOG = "https://catalog.gog.com/v1/catalog"
# Каталог ищет только текстом: на числовой запрос он отвечает `productCount: 0`,
# а `productIds` и `query=id:` игнорирует молча, отдавая случайную выдачу —
# проверено живьём 31.07.2026. Номер в название переводит эта ручка, и она же
# единственная у GOG умеет сказать «такого продукта нет».
PRODUCT = "https://api.gog.com/products/{source_id}"

# Дополнения и саундтреки отсеивает сам запрос: замерено, что по «Baldur's Gate»
# четырнадцать строк превращаются в шесть, по «baldurs gate 3» тринадцать в пять.
# Именно `game,pack`, а не `game` — добрую половину классики GOG продаёт
# комплектом, и `in:game` выбросил бы «Fallout 2», «Ведьмака 3», «Tyranny» и
# «Wasteland 2» вместе с DLC.
PRODUCT_TYPES = "in:game,pack"


class GogClient:
    """Поиск GOG никогда не отвечает «не найдено»: на бессмыслицу приезжает
    200 и два десятка несвязанных игр, на пустой запрос — весь каталог.

    Отсюда правило, которое этот клиент обязан держать: **из каталога `Missing`
    не приходит никогда.** Пустой список и чужая выдача — это «поиск
    отранжировал мимо», а не «игры в каталоге нет», и `search` отрицательного
    факта не даёт вовсе.

    Отрицательный факт дают два места, и каждое спрашивает не «что похоже», а
    «есть ли ровно это»: товарная ручка кодом 404 — у `card`, и точное
    совпадение слага — у `resolve_slug`. Оба читают его по разобранному телу.

    Аргумент `kind` есть ради общего контракта каталожных клиентов и
    игнорируется: у GOG содержимое одного типа."""

    def __init__(self, http: SourceHttp) -> None:
        self._http = http

    @property
    def name(self) -> str:
        """Под этим именем источник назовётся в отказе — в том числе в отказе,
        который соберёт не он сам, а поймавший его исключение сервис."""
        return self._http.name

    async def _payload(self, query: str,
                       product_types: str | None = None) -> dict | Refusal:
        """Тело ответа каталога. Разбирают его двое и по-разному: поиску нужны
        кандидаты, привязке — номер по слагу.

        Отсев рода товара спрашивает только поиск. У `card` и `resolve_slug`
        спрашивают не «что похоже», а «есть ли ровно это», и суженный вопрос
        превратил бы ссылку на дополнение в честное «такого нет» — то есть в
        ложный отрицательный факт."""
        narrow = {"productType": product_types} if product_types else {}
        response = await asked(
            self._http, CATALOG,
            {"query": f"like:{query}", "locale": "ru-RU", **narrow},
        )
        if isinstance(response, Refusal):
            return response
        return parsed(logger, "gog", "тело каталога не разобралось",
                      response.json)

    async def _catalog(self, query: str,
                       product_types: str | None = None) -> list | Refusal:
        payload = await self._payload(query, product_types)
        if isinstance(payload, Refusal):
            return payload
        return parsed(logger, "gog", "каталог не разобрался",
                      lambda: parse_catalog(payload))

    async def search(self, query: str, kind: Kind) -> Outcome:
        """Кандидаты собираются из тела ответа, а не из разобранных карточек:
        слаг лежит в строке каталога и нужен склейке выдачи ключом."""
        payload = await self._payload(query, PRODUCT_TYPES)
        if isinstance(payload, Refusal):
            return payload
        return parsed(logger, "gog", "выдача каталога не разобралась",
                      lambda: Found(parse_hits(payload)))

    async def _title(self, source_id: str) -> str | Outcome:
        """Название по номеру. Отдельный запрос — цена за то, что контракт у трёх
        магазинов один: снаружи карточка спрашивается номером, а каталог номера
        не понимает.

        Берём именно название, а не слаг: замерено на шести играх 31.07.2026 —
        по названию каталог находит нужную все шесть раз, по словам слага три из
        шести. Длинный слаг вроде `..._game_of_the_year_edition` уводит поиск на
        девять чужих игр, а тот же товар по названию отдаётся один."""
        response = await self._http.get(PRODUCT.format(source_id=source_id))
        if not isinstance(response, httpx.Response):
            return response
        if response.status_code == 404:
            # Тем же общим правилом, что у оценочных источников: 404 со
            # страницей вместо JSON — это чужой периметр, а не «игры нет».
            return absent(response, self._http.name)
        if response.status_code != 200:
            return refuse_undocumented(self._http, response.status_code)
        return parsed(logger, "gog", f"товар {source_id} не разобрался",
                      lambda: title_of(response.json()))

    async def card(self, source_id: str, kind: Kind) -> Outcome:
        """Номер переводится в название, и название уходит в каталог: строкой
        каталога карточка приезжает целиком, отдельной детальной ручки у GOG нет.

        Каталог не отдал нужный id — это «поиск отранжировал мимо», а не «игры
        нет»: спрашиваем мы конкретный идентификатор, но спрашиваем его у поиска
        по названию."""
        title = await self._title(source_id)
        if not isinstance(title, str):
            return title
        cards = await self._catalog(title)
        if isinstance(cards, Refusal):
            return cards
        for card in cards:
            if card.item.source_id == source_id:
                # Английское название достаётся даром: ручку мы уже спросили, а
                # локали у неё нет — она отвечает по-английски всегда. Каталог
                # при этом спрашивается с `ru-RU`, и в `title` лежит
                # локализованное. Раскладка полей — решение пользователя
                # 03.08.2026: `original_title` у игры всегда английское.
                return Found(replace(
                    card, item=replace(card.item, original_title=title)))
        return Refusal(
            source="gog",
            reason=Reason.BROKEN,
            detail=f"каталог не вернул {source_id}",
        )

    async def resolve_slug(self, slug: str) -> Outcome:
        """В адресе у GOG слаг, а каталогу нужен номер. Ручки «слаг → номер» у
        GOG нет вовсе — проверено живьём: `v2/games?slug` и `products?slug`
        параметр игнорируют. Значит спрашиваем каталог самим слагом, и берём
        только точное совпадение.

        Форм запроса две, и обе нужны: замерено на шести играх 31.07.2026 — слаг
        словами не находит `the_witcher_3_wild_hunt_game_of_the_year_edition`
        (каталог отдаёт девять чужих игр), слаг подчёркиваниями не находит
        коротких вроде `baldurs_gate_iii`. Каждая форма берёт три игры из шести,
        вместе — все шесть. Ложного срабатывания вторая попытка не добавляет:
        принимается только точное совпадение слага.

        `Missing` тут возвращается, хотя из `search` — никогда: здесь спрашивают
        не «что похоже на это название», а «есть ли ровно такой слаг», и его
        отсутствие — честный ответ. У `card` отрицательный факт свой, от товарной
        ручки."""
        # Слаг без подчёркиваний обе формы даёт одинаковыми, и второй запрос был
        # бы тем же самым: спрашиваем один раз.
        for query in unique((slug, slug.replace("_", " "))):
            payload = await self._payload(query)
            if isinstance(payload, Refusal):
                return payload
            found = parsed(logger, "gog",
                           f"каталог по слагу {slug} не разобрался",
                           lambda: find_slug(payload, slug))
            if isinstance(found, Refusal):
                return found
            if found is not None:
                return Found(found)

        logger.info("gog: слага %s в каталоге не нашлось", slug)
        return Missing()

    async def aclose(self) -> None:
        await self._http.aclose()
