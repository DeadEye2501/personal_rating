"""Записанные ответы источников: живьём тесты не ходят никуда."""

import httpx
import pytest

from tests.builders import recorded as _load


def _meta(relative: str) -> dict:
    """Код ответа и отобранные заголовки, записанные рядом с телом."""
    return _load(f"{relative.rsplit('.', 1)[0]}.meta.json")


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
