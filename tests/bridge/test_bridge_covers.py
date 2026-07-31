"""Мост: обложки — заливка своей картинки и наличие."""

import base64
from datetime import datetime

from backend.model import BadImage
from bridge.covers import Covers

PNG = base64.b64encode(b"\x89PNG\r\n\x1a\n").decode()


def test_an_uploaded_picture_arrives_as_bytes(spy, asked):
    """Внутрь картинка идёт base64: аргументы уезжают `postMessage`-ом, и этот
    канал бинарным тоже не бывает."""
    answers, log = asked
    answers["posters.store_upload"] = None

    before = datetime.now()
    Covers(spy).store_upload(12, PNG)
    after = datetime.now()

    name, args, _ = log[0]
    assert name == "posters.store_upload"
    assert args[0] == 12
    assert args[1] == b"\x89PNG\r\n\x1a\n"
    assert before <= args[2] <= after


def test_not_a_picture_is_a_kind_of_failure(spy, asked):
    """Обрезка до 2:3 идёт на бэкенде, и негодный файл он же и распознаёт."""
    answers, _ = asked
    answers["posters.store_upload"] = BadImage("не картинка")

    assert Covers(spy).store_upload(12, PNG)["fail"] == "bad-image"


def test_broken_base64_does_not_reach_the_backend(spy, asked):
    """Мусор нарочно из латиницы: кириллица падает раньше проверки алфавита, и
    на ней строгость разбора не наблюдалась бы вовсе — картинка с приписанным
    хвостом доехала бы до бэкенда."""
    _, log = asked

    assert Covers(spy).store_upload(12, PNG + "!!")["fail"] == "bad-image"
    assert log == []


def test_having_a_cover_is_a_plain_answer(spy, asked):
    answers, log = asked
    answers["posters.has"] = True

    assert Covers(spy).has(12) == {"ok": True}
    assert log == [("posters.has", (12,), {})]
