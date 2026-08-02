"""Разрешение чужих меток карточки: то, что видно в самом списке наших номеров.

Через базу это не проверить: повторяющийся номер жанра `item_genre` принимает
молча, и набор жанров карточки от повтора не меняется. Значит, смотреть надо на
возвращённый список.

Правила как таковые сторожит `test_genre_rules.py` — на настоящем справочнике.
Здесь проверяется то, чего он не видит: пространства меток и снятие повторов
между ними."""

import logging

import pytest

from backend.model import GenreSource
from backend.service.genres import resolved_genres
from backend.storage.repository.genres import GenresRepository
from tests.conftest import ours, seed

REFERENCE = (
    "INSERT INTO genre (id, name, kind) VALUES "
    "(1, 'Racing', 'game'), (2, 'Strategy', 'game'), (3, 'RPG', 'game')"
)
# `9` у Steam — это «Гонки», а у GOG слаг `9` не значит ничего; два разных тега
# Steam ведут в один наш `RPG` — повтор бывает и внутри пространства, и между
# ними.
RULES = (
    "INSERT INTO genre_rule (id, source, genre_id, alone) VALUES "
    "(1, 'steam', 1, 0), (2, 'gog', 2, 0), "
    "(3, 'steam', 3, 0), (4, 'steam', 3, 0), (5, 'gog', 3, 0)"
)
MARKS = (
    "INSERT INTO genre_rule_mark (rule_id, ext_id, forbidden) VALUES "
    "(1, '9', 0), (2, '9', 0), (3, '100', 0), (4, '200', 0), (5, 'rpg', 0)"
)


@pytest.fixture
async def genres(engine, sessions):
    await seed(engine, REFERENCE, RULES, MARKS)
    return GenresRepository(sessions)


async def test_spaces_are_asked_apart(genres):
    """Спрошенные вместе, `9` у Steam и `9` у GOG дали бы карточке чужой жанр —
    или один вместо двух.

    Порядок сверяется, а не набор: пространства спрашиваются в том порядке, в
    каком пришли, и первым в списке оказывается Steam."""
    found = await resolved_genres(genres, (
        (GenreSource.STEAM, "9"), (GenreSource.GOG, "9"),
    ))

    assert found == [1, 2]


async def test_the_order_of_the_spaces_is_the_order_of_the_answer(genres):
    """Обратный порядок на входе — обратный на выходе. Снятие повторов порядок
    не меняет: `set` его не помнит, а словарь помнит."""
    found = await resolved_genres(genres, (
        (GenreSource.GOG, "9"), (GenreSource.STEAM, "9"),
    ))

    assert found == [2, 1]


async def test_one_genre_from_two_marks_is_returned_once(genres):
    found = await resolved_genres(genres, (
        (GenreSource.STEAM, "100"), (GenreSource.STEAM, "200"),
    ))

    assert found == [3]


async def test_one_genre_from_two_spaces_is_returned_once(genres):
    """Повтор бывает и между пространствами: внутри одного его снимает разбор
    правил, между ними — только здесь. Тег `100` у Steam и слаг `rpg` у GOG оба
    ведут в `RPG`, и вернуться он должен один раз."""
    found = await resolved_genres(genres, (
        (GenreSource.STEAM, "100"), (GenreSource.GOG, "rpg"),
    ))

    assert found == [3]


async def test_nothing_known_gives_an_empty_list(genres, caplog):
    """Незнакомая метка не заводит жанра, не роняет разрешение и не пишет в
    лог: справочник пополняют руками, когда владелец сам этого захочет."""
    with caplog.at_level(logging.DEBUG):
        found = await resolved_genres(genres, ((GenreSource.GOG, "нет такого"),))

    assert found == []
    assert ours(caplog) == []


async def test_nothing_marked_is_nothing_resolved(genres):
    """Пустой набор меток — не повод падать. Про «не повод идти в базу» здесь
    не утверждается: пропущенный запрос не наблюдается — пустой справочник дал
    бы ту же пустоту."""
    assert await resolved_genres(genres, ()) == []
