"""На каком языке написано название.

Нужно затем, чтобы разложить два имени игры по своим полям: `title` — язык
оригинала либо русская локализация, `original_title` — всегда английское.
Решение пользователя 03.08.2026.
"""

import pytest

from backend.language import in_russian

RUSSIAN = [
    "Ведьмак 3: Дикая Охота",
    "Космические Рейнджеры HD: Революция",
    "Ил-2 Штурмовик",
    # Смешанное: латиница вперемешку с кириллицей — всё равно русское.
    "King's Bounty: Легенда о рыцаре",
    "Кровная вражда: Ведьмак. Истории",
]

NOT_RUSSIAN = [
    "The Witcher 3: Wild Hunt",
    "Space Rangers HD: A War Apart",
    "Baldur's Gate 3",
    # Не английское, но и не русское: для этой функции разницы нет, и это
    # записано в её докстринге. Обе строки пойдут в поле английского названия.
    "Trüberbrook",
    "FINAL FANTASY VII",
    "Postal²",
]


@pytest.mark.parametrize("name", RUSSIAN)
def test_a_name_with_cyrillic_is_russian(name):
    assert in_russian(name) is True


@pytest.mark.parametrize("name", NOT_RUSSIAN)
def test_a_name_without_cyrillic_is_not_russian(name):
    assert in_russian(name) is False


def test_nothing_is_not_russian():
    """Пустое имя — не русское, а не «неизвестно». Ответ тут двоичный по
    построению: у названия два места, и третьего нет."""
    assert in_russian("") is False


def test_the_answer_does_not_depend_on_the_case():
    """Кириллица бывает прописной, и «ВЕДЬМАК» — то же слово."""
    assert in_russian("ВЕДЬМАК 3") is True


def test_the_letter_yo_counts():
    """`ё` и `Ё` стоят в Unicode отдельно от основного кириллического
    диапазона, и проверка по одному диапазону объявила бы «Ёжик» английским."""
    assert in_russian("Ёжик") is True
    assert in_russian("ёж") is True
