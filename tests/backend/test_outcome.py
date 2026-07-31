"""Три исхода запроса к источнику: что обязательно, что неизменно и как причина
читается строкой.

Только `backend/model/outcome.py`: сборка отказа по неразобранному телу живёт в
`backend/sources/errors.py`, прямых тестов не имеет и сторожится у клиентов
источников, где из неё что-то следует.

Обязательность полей проверяется, а значения умолчаний — нет: сроки годности и
подробность отказа сторожатся там, где из них что-то следует, — у клиентов, которые
их называют."""

from dataclasses import FrozenInstanceError

import pytest

from backend.model import Found, Reason, Refusal


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


def test_outcome_cannot_be_changed_by_whoever_received_it():
    """Исход уходит нескольким потребителям сразу, и правка одним из них
    испортила бы его остальным."""
    refusal = Refusal(source="omdb", reason=Reason.QUOTA)
    with pytest.raises(FrozenInstanceError):
        refusal.reason = Reason.KEY
    with pytest.raises(FrozenInstanceError):
        Found(8.6).value = 1.0
