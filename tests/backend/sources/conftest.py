"""Записанные ответы источников: живьём тесты не ходят никуда."""

import json
from datetime import datetime, timedelta
from pathlib import Path

import httpx
import pytest

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


class FakeClock:
    """Часы, которые двигают руками: иначе срок предохранителя проверяется
    только `sleep`-ом на минуту."""

    def __init__(self) -> None:
        self.now = datetime(2026, 7, 27, 12, 0)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, delta: timedelta) -> None:
        self.now += delta


def _load(relative: str):
    path = FIXTURES / relative
    text = path.read_text(encoding="utf-8")
    return json.loads(text) if path.suffix == ".json" else text


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
