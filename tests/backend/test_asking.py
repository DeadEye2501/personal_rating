"""Что `answered` делает с сорвавшимся запросом и что — с отменой."""

import asyncio

import pytest

from backend.model import Found, Reason, Refusal
from backend.service.asking import answered
from tests.conftest import ours


async def broken_request():
    raise KeyError("payload")


async def cancelled_request():
    raise asyncio.CancelledError


async def good_request():
    return Found("оценки")


async def test_an_answer_passes_through_untouched():
    """Обёртка не встаёт между сервисом и исходом: до неё доходит то же, что
    отдал клиент."""
    assert await answered(good_request(), "omdb") == Found("оценки")


async def test_an_unexpected_exception_becomes_a_refusal():
    """Клиенты ловят только провод и разбор. Всё остальное — чужая библиотека,
    наша опечатка — вылетело бы из сервиса наружу, а у границы потоков второго
    канала доставки нет."""
    result = await answered(broken_request(), "omdb")

    assert isinstance(result, Refusal)
    assert (result.source, result.reason) == ("omdb", Reason.BROKEN)


async def test_the_refusal_is_named_by_the_source_it_was_asked_of():
    """Имя нужно плашке: человек должен увидеть, кто именно не ответил. Тот же
    сорвавшийся запрос к другому источнику называется иначе."""
    result = await answered(broken_request(), "kinopoisk")

    assert result.source == "kinopoisk"


async def test_a_broken_request_leaves_a_traceback_in_the_log(caplog):
    """Отказ уносит наверх только причину, а починить по ней нельзя: `KeyError`
    в разборе и обрыв соединения дают один `BROKEN`. Трассировка остаётся здесь
    или не остаётся нигде."""
    with caplog.at_level("ERROR"):
        await answered(broken_request(), "omdb")

    assert any("omdb" in message for message in ours(caplog))
    assert "KeyError" in caplog.text


async def test_cancellation_is_not_turned_into_a_refusal():
    """Отмена — наследник `BaseException`, и гасят ею нас, а не источник.
    Превратить её в отказ значит соврать про закрытие приложения: тот, кто
    отменял, ждёт отмены, а получил бы обычный ответ и продолжил работу."""
    with pytest.raises(asyncio.CancelledError):
        await answered(cancelled_request(), "omdb")


async def test_a_cancelled_request_leaves_nothing_in_the_log(caplog):
    """Отмена — не происшествие. Записанная как сорвавшийся запрос, она засорила
    бы лог трассировкой на каждое закрытие окна."""
    with caplog.at_level("ERROR"), pytest.raises(asyncio.CancelledError):
        await answered(cancelled_request(), "omdb")

    assert ours(caplog) == []
