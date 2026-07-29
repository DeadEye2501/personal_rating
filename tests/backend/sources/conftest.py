"""Записанные ответы источников: живьём тесты не ходят никуда."""

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _load(relative: str):
    path = FIXTURES / relative
    text = path.read_text(encoding="utf-8")
    return json.loads(text) if path.suffix == ".json" else text


@pytest.fixture
def fixture():
    """Тело записанного ответа. JSON разбирается, всё прочее идёт текстом."""
    return _load
