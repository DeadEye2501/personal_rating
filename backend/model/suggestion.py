"""Строка подсказки при вводе имени человека или студии."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Suggestion:
    """`hint` — название карточки, по которой этого человека узнают,
    `hint_item_id` — она же для показа обложки. Пусты только у того, за кем в
    библиотеке пока ничего не числится."""

    entity_id: int
    name: str
    hint: str
    hint_item_id: int | None
