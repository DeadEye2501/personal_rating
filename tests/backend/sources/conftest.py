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
