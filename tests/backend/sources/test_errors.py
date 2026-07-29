from dataclasses import FrozenInstanceError
from datetime import timedelta

import pytest

from backend.sources.errors import (
    Found,
    Missing,
    Reason,
    Refusal,
    is_answer,
    writable,
)


def test_found_carries_the_value():
    assert Found(8.6).value == 8.6


def test_missing_is_an_answer_not_a_silence():
    """«У источника такого нет» — это ответ, и его надо записать пустым
    значением, иначе фильм будет перезапрашиваться при каждом показе."""
    assert is_answer(Missing()) is True
    assert writable(Missing()) is True


def test_refusal_is_not_an_answer_and_is_not_written():
    refusal = Refusal(source="omdb", reason=Reason.QUOTA)
    assert is_answer(refusal) is False
    assert writable(refusal) is False


def test_found_is_both():
    assert is_answer(Found(1.0)) is True
    assert writable(Found(1.0)) is True


def test_refusal_may_name_its_own_retry_delay():
    refusal = Refusal(source="mdblist", reason=Reason.QUOTA,
                      retry_after=timedelta(hours=3))
    assert refusal.retry_after == timedelta(hours=3)


def test_refusal_without_a_named_delay():
    """Не все источники называют срок: у OMDB заголовков нет вовсе."""
    assert Refusal(source="omdb", reason=Reason.QUOTA).retry_after is None


def test_refusal_carries_what_the_source_said_and_is_silent_without_it():
    """Подробность — это чужой текст отказа, и по умолчанию её нет: причина
    известна не из него, а из кода ответа."""
    assert Refusal(source="omdb", reason=Reason.KEY,
                   detail="Invalid API key!").detail == "Invalid API key!"
    assert Refusal(source="omdb", reason=Reason.KEY).detail == ""


def test_refusal_takes_its_fields_in_the_written_order():
    """Порядком полей отказ и строится: перепутанные местами имя с причиной
    разошлись бы молча — оба строки."""
    refusal = Refusal("omdb", Reason.QUOTA, timedelta(hours=3), "quota reached")
    assert refusal.source == "omdb"
    assert refusal.reason == Reason.QUOTA
    assert refusal.retry_after == timedelta(hours=3)
    assert refusal.detail == "quota reached"


def test_neither_outcome_can_be_built_empty():
    """Отказ без причины и находка без находки — это не исходы, а недосмотр
    вызывающего, и увидеть его надо на месте, а не по пустому полю потом."""
    with pytest.raises(TypeError):
        Refusal(source="omdb")
    with pytest.raises(TypeError):
        Found()


def test_reason_reads_as_its_own_value_wherever_a_string_is_expected():
    """Причина уходит в лог и в сообщение подстановкой, а не через `.value`:
    обычное перечисление даст там «Reason.QUOTA» и сравняется с «quota» в
    ложь, оставаясь неотличимым, пока тест читает атрибут."""
    assert f"причина: {Reason.QUOTA}" == "причина: quota"
    assert Reason.QUOTA == "quota"


def test_reasons_cover_every_way_a_source_can_refuse():
    """Сверяется пара имя-значение, а не множество значений: по именам причину
    выбирает код, значения уходят в лог, и перепутанные местами они дают
    зелёное множество при вранье в обеих строках."""
    assert {r.name: r.value for r in Reason} == {
        "QUOTA": "quota",
        "RATE": "rate",
        "KEY": "key",
        "NETWORK": "network",
        "BROKEN": "broken",
    }


def test_outcome_cannot_be_changed_by_whoever_received_it():
    """Исход уходит нескольким потребителям сразу, и правка одним из них
    испортила бы его остальным."""
    refusal = Refusal(source="omdb", reason=Reason.QUOTA)
    with pytest.raises(FrozenInstanceError):
        refusal.reason = Reason.KEY
    with pytest.raises(FrozenInstanceError):
        Found(8.6).value = 1.0
