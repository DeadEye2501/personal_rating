"""Общее для проверок источников: тела ответов и строители клиентов."""

import asyncio

import httpx
import pytest

from backend.sources.http import SourceHttp
from backend.sources.ratings.kinopoisk.unofficial import UnofficialClient
from tests.builders import recorded as _load
from tests.fakes import counting


def unofficial(transport) -> UnofficialClient:
    """Запасное зеркало Кинопоиска на заданном транспорте.

    Здесь, а не в модуле проверок: его спрашивают двое — свой модуль зеркала и
    модуль пары «основное плюс запасное», — и своими копиями они разъехались бы
    молча."""
    return UnofficialClient(SourceHttp("kinopoisk", transport=transport),
                            api_key="k")


def _meta(relative: str) -> dict:
    """Код ответа и отобранные заголовки, записанные рядом с телом."""
    return _load(f"{relative.rsplit('.', 1)[0]}.meta.json")


def keys_of_google(exhausted: str, delay: float = 0.0):
    """Транспорт Google Books, у которого названный ключ исчерпал суточную
    квоту, и список ключей, ушедших на провод.

    Здесь, а не в модулях проверок: запасной ключ наблюдают трое — клиент, его
    гонка и боевая сборка, — и своими копиями они разъехались бы молча.

    Список ушедшего ведёт общий `counting`, а не свой: развилка здесь по
    **значению** ключа, а не по числу запросов, — значит счёт нужен после
    ответа, и своего транспорту не требуется.

    `delay` держит ответ исчерпанного ключа: без задержки два одновременных
    запроса уходят по очереди, и гонки, ради которой оговорка про соседа и
    написана, не выходит вовсе. Обработчик асинхронный всегда — `MockTransport`
    принимает и такой, а два его вида были бы вторым объявлением одного и того
    же."""
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.params.get("key") == exhausted:
            if delay:
                await asyncio.sleep(delay)
            return httpx.Response(429, json={"error": {"code": 429}})
        return httpx.Response(200, json={"items": []})

    return counting(httpx.MockTransport(handler))


def keys_of(seen: list) -> list[str]:
    """Ключи, ушедшие на провод, из списка запросов: спрашивают их трое."""
    return [one.url.params.get("key") for one in seen]


@pytest.fixture
def fixture():
    """Тело записанного ответа. JSON разбирается, всё прочее идёт текстом."""
    return _load


@pytest.fixture
def meta():
    return _meta


@pytest.fixture
def gog_catalog():
    """Обработчик каталога GOG, отвечающий как живой: с `productType` сужает
    выдачу до названных родов, без него отдаёт всё, на непонятое — пустоту.

    Записанным ответом тут не обойтись: подмена готовой выдачи на точное
    значение параметра не различает `in:game` и `in:game,pack`, а именно на этом
    различии держится решение (комплектом продаётся половина классики).

    Поведение замерено 03.08.2026 по «Baldur's Gate»: без параметра 14 строк,
    `in:game,pack` и `game,pack` — по 6, `in:game` — 5, мусор — 0. Префикс `in:`
    каталог не требует, поэтому и эмуляция его не требует."""
    whole = _load("gog/catalog.json")

    def handler(request: httpx.Request) -> httpx.Response:
        asked = request.url.params.get("productType") or ""
        kinds = set(asked.removeprefix("in:").split(",")) if asked else None
        rows = [one for one in whole["products"]
                if kinds is None or one["productType"] in kinds]
        return httpx.Response(200, json={**whole, "products": rows})

    return handler


@pytest.fixture
def replay():
    """Транспорт, отвечающий записанным ответом целиком — с его кодом и
    заголовками, а не одним телом. Классификация отказов смотрит именно на
    код, и подстановка тела под чужой код проверяла бы не то.

    Файлов можно передать несколько: они отдаются по порядку запросов, а
    последний — на все оставшиеся. Это нужно там, где одна операция ходит в
    две ручки: у Steam карточка приезжает из `appdetails`, а её теги —
    отдельным запросом."""

    def build(*relatives: str) -> httpx.MockTransport:
        answers = []
        for relative in relatives:
            body = _load(relative)
            answers.append((
                _meta(relative),
                {"json": body} if isinstance(body, dict | list) else {"text": body},
            ))

        served = iter(answers)
        last = answers[-1]

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal last
            last = next(served, last)
            info, payload = last
            return httpx.Response(
                info["status"], headers=info.get("headers", {}), **payload
            )

        return httpx.MockTransport(handler)

    return build
