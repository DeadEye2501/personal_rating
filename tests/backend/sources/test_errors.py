"""Три исхода запроса к источнику и отказ по неразобранному ответу.

Поля и умолчания `@dataclass` здесь не проверяются: уронить их можно только
правкой объявления, а она тут же роняет десяток настоящих тестов. Сроки годности и
подробность отказа сторожатся там, где из них что-то следует, — у клиентов
источников."""

from dataclasses import FrozenInstanceError

import pytest

from backend.model import Found, Missing, Reason, Refusal, is_answer


def test_missing_is_an_answer_not_a_silence():
    """«У источника такого нет» — это ответ, и его надо записать пустым
    значением, иначе фильм будет перезапрашиваться при каждом показе."""
    assert is_answer(Missing()) is True


def test_refusal_is_not_an_answer():
    assert is_answer(Refusal(source="omdb", reason=Reason.QUOTA)) is False


def test_found_is_an_answer_too():
    assert is_answer(Found(1.0)) is True


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
