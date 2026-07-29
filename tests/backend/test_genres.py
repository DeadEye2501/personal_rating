import logging

import pytest

from backend.model import GenreKind, GenreSource, Kind
from backend.storage.repository.genres import GenresRepository
from tests.conftest import ours, seed


@pytest.fixture
async def reference(engine):
    """Справочник кладётся руками, а не миграцией: проверяется разрешение
    идентификаторов, а не содержимое справочника — его сторожит
    `test_genre_reference.py`."""
    await seed(
        engine,
        "INSERT INTO genre (id, name, kind) VALUES "
        "(1, 'Боевик', 'film'), (2, 'Приключения', 'film'), "
        "(3, 'Драма', 'film'), (4, 'ролевая', 'game')",
        "INSERT INTO genre_map (source, ext_id, genre_id) VALUES "
        "('tmdb', '28', 1), ('tmdb', '12', 2), ('tmdb', '18', 3), "
        "('tmdb', '10759', 1), ('tmdb', '10759', 2), "
        "('steam', '3', 4)",
    )


async def test_plain_identifier_resolves_to_one_genre(sessions, reference):
    assert await GenresRepository(sessions).resolve(GenreSource.TMDB, ["18"]) == [3]


async def test_composite_identifier_unfolds_into_two(sessions, reference):
    resolved = await GenresRepository(sessions).resolve(GenreSource.TMDB, ["10759"])
    assert sorted(resolved) == [1, 2]


async def test_overlapping_identifiers_do_not_duplicate(sessions, reference):
    resolved = await GenresRepository(sessions).resolve(GenreSource.TMDB, ["10759", "28"])
    assert sorted(resolved) == [1, 2]


SILENT = [
    ("незнакомый жанр", GenreSource.GOG, "совсем-новый-жанр"),
    ("отвергнутый слаг", GenreSource.GOG, "fpp"),
    ("незнакомый тег", GenreSource.GOG_TAG, "atmospheric"),
    ("незнакомый номер", GenreSource.TMDB, "99999"),
]


@pytest.mark.parametrize(("case", "source", "ext_id"), SILENT,
                         ids=[one[0] for one in SILENT])
async def test_what_is_not_in_the_reference_is_dropped_without_a_word(
    sessions, reference, caplog, case, source, ext_id
):
    """Чего нет в таблице соответствий — то молча отбрасывается, откуда бы оно
    ни пришло. Лог не ведём: читать его никто не будет, а справочник пополняют
    руками, когда владелец сам этого захочет.

    Смотрим на свои записи, а не на весь лог: на уровне отладки в него сыпет
    сам драйвер базы."""
    with caplog.at_level(logging.DEBUG):
        assert await GenresRepository(sessions).resolve(source, [ext_id]) == []
    assert ours(caplog) == []


async def test_the_known_part_survives_the_unknown(sessions, reference, caplog):
    """Незнакомое рядом со знакомым не мешает знакомому доехать."""
    with caplog.at_level(logging.DEBUG):
        resolved = await GenresRepository(sessions).resolve(
            GenreSource.TMDB, ["18", "99999"]
        )
    assert resolved == [3]
    assert ours(caplog) == []


async def test_nothing_asked_is_nothing_resolved(sessions, reference):
    """Пустой список — не повод идти в базу и не повод падать."""
    assert await GenresRepository(sessions).resolve(GenreSource.TMDB, []) == []


async def test_sources_do_not_leak_into_each_other(sessions, reference):
    # У Steam свой словарь: id 3 у него ролевая, а не драма.
    assert await GenresRepository(sessions).resolve(GenreSource.STEAM, ["3"]) == [4]
    assert await GenresRepository(sessions).resolve(GenreSource.TMDB, ["3"]) == []


async def test_set_and_read_genres_of_a_card(sessions, reference, card):
    item_id = await card()
    repository = GenresRepository(sessions)

    await repository.set_for_item(item_id, [2, 3])
    names = [genre.name for genre in await repository.genres_of(item_id)]
    # Пара выбрана так, что алфавит обратен номерам строк: «Приключения» — это
    # 2, «Драма» — 3. Сортировка по номеру дала бы обратный порядок, а на паре
    # «Боевик» и «Драма» совпала бы с алфавитом и прошла молча.
    assert names == ["Драма", "Приключения"]


async def test_genres_come_back_with_their_set(sessions, reference, card):
    """Наружу едет `Genre`, а не строка базы: `kind` обязан быть перечислением,
    иначе он не сравнится с `GenreKind.FILM` там, где по нему фильтруют.

    Наборов два и проверяются оба: с одним киношным жанром тест зеленел бы и
    при наглухо зашитом `GenreKind.FILM`."""
    film_card = await card(source_id="1")
    game_card = await card(Kind.GAME, "2")
    repository = GenresRepository(sessions)
    await repository.set_for_item(film_card, [1])
    await repository.set_for_item(game_card, [4])

    film = (await repository.genres_of(film_card))[0]
    game = (await repository.genres_of(game_card))[0]
    assert (film.id, film.kind) == (1, GenreKind.FILM)
    assert (game.id, game.kind) == (4, GenreKind.GAME)
    assert isinstance(film.kind, GenreKind)


async def test_setting_genres_replaces_the_previous_set(sessions, reference, card):
    item_id = await card()
    repository = GenresRepository(sessions)

    await repository.set_for_item(item_id, [1, 3])
    await repository.set_for_item(item_id, [2])
    names = [genre.name for genre in await repository.genres_of(item_id)]
    assert names == ["Приключения"]


async def test_setting_genres_touches_only_its_card(sessions, reference, card):
    """Замена набора чистит прежний только у своей карточки."""
    mine = await card(source_id="1")
    other = await card(source_id="2")
    repository = GenresRepository(sessions)
    await repository.set_for_item(mine, [1])
    await repository.set_for_item(other, [3])

    await repository.set_for_item(mine, [2])

    names = [genre.name for genre in await repository.genres_of(other)]
    assert names == ["Драма"]


async def test_a_repeated_genre_is_written_once(sessions, reference, card):
    """В набор приходит что угодно: сборный жанр разворачивается в два, и два
    разных идентификатора приводят к одному нашему. Повтор не должен ронять
    запись."""
    item_id = await card()
    repository = GenresRepository(sessions)

    await repository.set_for_item(item_id, [1, 1, 3])

    names = [genre.name for genre in await repository.genres_of(item_id)]
    assert names == ["Боевик", "Драма"]


async def test_an_empty_set_clears_the_genres(sessions, reference, card):
    item_id = await card()
    repository = GenresRepository(sessions)
    await repository.set_for_item(item_id, [1, 3])

    await repository.set_for_item(item_id, [])

    assert await repository.genres_of(item_id) == []


async def test_list_for_kind_keeps_the_two_sets_apart(sessions, reference):
    """Киношный список сравнивается целиком и в порядке по названию: в
    справочнике он лежит не по алфавиту, и сортировка по номеру строки дала бы
    другой порядок."""
    repository = GenresRepository(sessions)
    film = [genre.name for genre in await repository.list_for_kind(GenreKind.FILM)]
    game = [genre.name for genre in await repository.list_for_kind(GenreKind.GAME)]
    assert film == ["Боевик", "Драма", "Приключения"]
    assert game == ["ролевая"]
