"""Строка подсказки при вводе имени человека или студии."""

from dataclasses import dataclass

from backend.model.kinds import Kind


@dataclass(frozen=True, slots=True)
class Suggestion:
    """`hint` — название карточки, по которой этого человека узнают,
    `hint_item_id` — она же для показа обложки, `hint_kind` — её тип
    содержимого. Пусты только у того, за кем в библиотеке пока ничего не
    числится.

    Тип нужен форме рамки: обложка альбома квадратная, и взять его у правимой
    карточки нельзя — человек бывает и в фильмах, и в альбомах, а подсказка
    показывает его самое высоко оценённое, какого бы типа оно ни было."""

    entity_id: int
    name: str
    hint: str
    hint_item_id: int | None
    hint_kind: Kind | None
