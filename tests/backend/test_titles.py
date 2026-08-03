"""Приведение чужого названия к сравнимому виду.

Правила замерены 03.08.2026 на 1354 строках выдачи: каждое из них убирает
расхождение, на котором две записи одной игры расходились ключом."""

import pytest

from backend.service.titles import flattened, without_edition

SAME = [
    ("римские и арабские", "Fallout II", "Fallout 2"),
    ("товарный знак", "DARK SOULS™ III", "Dark Souls 3"),
    ("охраняемый знак", "Warcraft® III", "Warcraft 3"),
    ("союз словом и знаком", "Command and Conquer", "Command & Conquer"),
    ("артикль", "The Witcher", "Witcher"),
    ("регистр и знаки препинания", "FALLOUT: New Vegas!", "fallout new vegas"),
    ("длинное тире", "Fallout — New Vegas", "Fallout - New Vegas"),
]


@pytest.mark.parametrize(("case", "one", "other"), SAME,
                         ids=[one[0] for one in SAME])
def test_two_writings_of_one_name_flatten_alike(case, one, other):
    assert flattened(one) == flattened(other) != ""


def test_the_trademark_is_removed_before_the_letters_appear():
    """Знак снимается **до** `NFKC`, и это не придирка: нормализация
    разворачивает «™» в буквы «TM» и приклеивает их к слову — «SOULS™» стало бы
    «soulstm», то есть новым словом, и ключ разошёлся бы."""
    assert "tm" not in flattened("DARK SOULS™").split()


EDITIONS = [
    ("Fallout 3: Game of the Year Edition", "Fallout 3"),
    ("The Witcher 3: Wild Hunt - Complete Edition", "The Witcher 3: Wild Hunt"),
    ("Doom Eternal Deluxe", "Doom Eternal"),
]


@pytest.mark.parametrize(("dressed", "plain"), EDITIONS)
def test_the_edition_tail_does_not_change_the_key(dressed, plain):
    """Издания одной игры — одна игра, решение пользователя 02.08.2026."""
    assert without_edition(dressed) == without_edition(plain) != ""


def test_an_edition_word_inside_the_name_stays():
    """Снимается только хвост, а не слова где попало. «Game», «of» и «the» —
    издательские, и отсев по всей строке оставил бы от «The Game of Life» одну
    «life», склеив её со всем подряд.

    Проверяется расхождение, а не совпадение: тут ошибка выглядит как лишняя
    склейка, и заметить её на равенстве нельзя."""
    assert without_edition("The Game of Life") != without_edition("Life")
    assert "game" in without_edition("The Game of Life").split()


def test_a_name_made_only_of_edition_words_keeps_itself():
    """Снять хвост целиком — значит получить пустой ключ, а пустой ключ
    склеивает всё со всем. Такая строка остаётся собой."""
    assert without_edition("Collection") == flattened("Collection") != ""


def test_nothing_flattens_to_nothing():
    assert flattened("") == ""
    assert without_edition("") == ""


def test_different_games_keep_different_keys():
    """Приведение сближает написания одной игры, а не разные игры. Пара выбрана
    та, на которой второе название old-games однажды и склеило разное."""
    assert without_edition("Worms") != without_edition("Worms 2")
    assert without_edition("Space Quest I") != without_edition("Space Quest II")
