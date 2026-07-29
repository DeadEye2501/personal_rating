"""Разрешение чужих меток жанров: то, что видно в самом списке наших номеров.

Через базу это не проверить: повторяющийся номер жанра `item_genre` принимает
молча, и набор жанров карточки от повтора не меняется. Значит, смотреть надо на
возвращённый список."""

import pytest

from backend.model import GenreSource
from backend.service.genres import resolved_genres
from backend.storage.repository.genres import GenresRepository
from tests.conftest import seed

REFERENCE = (
    "INSERT INTO genre (id, name, kind) VALUES "
    "(1, 'Racing', 'game'), (2, 'Strategy', 'game'), (3, 'RPG', 'game')"
)
# `9` у Steam — это жанр «Гонки» и тег «Стратегия» одновременно; два разных тега
# ведут в один наш `RPG`, и жанр `77` ведёт туда же — повтор бывает и между
# пространствами.
MAP = (
    "INSERT INTO genre_map (source, ext_id, genre_id) VALUES "
    "('steam', '9', 1), ('steam_tag', '9', 2), "
    "('steam_tag', '100', 3), ('steam_tag', '200', 3), ('steam', '77', 3)"
)


@pytest.fixture
async def genres(engine, sessions):
    await seed(engine, REFERENCE, MAP)
    return GenresRepository(sessions)


async def test_spaces_are_asked_apart(genres):
    """Спрошенные вместе, жанр и тег с номером `9` дали бы карточке чужой
    жанр — или один вместо двух."""
    found = await resolved_genres(genres, (
        (GenreSource.STEAM, "9"), (GenreSource.STEAM_TAG, "9"),
    ))

    assert sorted(found) == [1, 2]


async def test_one_genre_from_two_tags_is_returned_once(genres):
    found = await resolved_genres(genres, (
        (GenreSource.STEAM_TAG, "100"), (GenreSource.STEAM_TAG, "200"),
    ))

    assert found == [3]


async def test_one_genre_from_two_spaces_is_returned_once(genres):
    """Повтор бывает и между пространствами: внутри одного его снимает сам
    справочник, между ними — только здесь. Тег `100` и жанр `77` оба ведут в
    `RPG`, и вернуться он должен один раз."""
    found = await resolved_genres(genres, (
        (GenreSource.STEAM_TAG, "100"), (GenreSource.STEAM, "77"),
    ))

    assert found == [3]


async def test_nothing_known_gives_an_empty_list(genres):
    """Незнакомая метка не заводит жанра и не роняет разрешение."""
    assert await resolved_genres(genres, ((GenreSource.GOG, "нет такого"),)) == []
