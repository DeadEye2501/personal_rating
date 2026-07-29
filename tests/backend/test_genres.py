import logging

import pytest
from sqlalchemy import text

from backend.model import GenreKind, GenreSource, Kind
from backend.storage.repository.genres import GenresRepository


@pytest.fixture
async def reference(engine):
    """Справочник кладётся руками, а не миграцией: проверяется разрешение
    идентификаторов, а не содержимое справочника — его сторожит
    `test_genre_reference.py`."""
    async with engine.begin() as connection:
        await connection.execute(text(
            "INSERT INTO genre (id, name, kind) VALUES "
            "(1, 'Боевик', 'film'), (2, 'Приключения', 'film'), "
            "(3, 'Драма', 'film'), (4, 'ролевая', 'game')"
        ))
        await connection.execute(text(
            "INSERT INTO genre_map (source, ext_id, genre_id) VALUES "
            "('tmdb', '28', 1), ('tmdb', '12', 2), ('tmdb', '18', 3), "
            "('tmdb', '10759', 1), ('tmdb', '10759', 2), "
            "('steam', '3', 4)"
        ))


async def test_plain_identifier_resolves_to_one_genre(sessions, reference):
    assert await GenresRepository(sessions).resolve(GenreSource.TMDB, ["18"]) == [3]


async def test_composite_identifier_unfolds_into_two(sessions, reference):
    resolved = await GenresRepository(sessions).resolve(GenreSource.TMDB, ["10759"])
    assert sorted(resolved) == [1, 2]


async def test_overlapping_identifiers_do_not_duplicate(sessions, reference):
    resolved = await GenresRepository(sessions).resolve(GenreSource.TMDB, ["10759", "28"])
    assert sorted(resolved) == [1, 2]


async def test_unknown_identifier_is_logged_and_skipped(sessions, reference, caplog):
    with caplog.at_level(logging.WARNING):
        resolved = await GenresRepository(sessions).resolve(
            GenreSource.TMDB, ["18", "99999"]
        )
    assert resolved == [3]
    assert "99999" in caplog.text


async def test_a_known_identifier_is_not_logged(sessions, reference, caplog):
    """Обратная половина: в лог попадает незнакомое, а не всё подряд."""
    with caplog.at_level(logging.WARNING):
        await GenresRepository(sessions).resolve(GenreSource.TMDB, ["18"])
    assert caplog.text == ""


async def test_nothing_asked_is_nothing_resolved(sessions, reference, caplog):
    with caplog.at_level(logging.WARNING):
        assert await GenresRepository(sessions).resolve(GenreSource.TMDB, []) == []
    assert caplog.text == ""


async def test_an_unmarked_tag_is_not_news(sessions, reference, caplog):
    """Спека запрещает писать неразмеченные теги в лог: словарь у тегов
    открытый, 432 метки у Steam и 203 у GOG, и большинство жанрами не являются
    вовсе. Пиши мы их — на каждой карточке в лог сыпалось бы полтора десятка
    строк, и настоящее расширение справочника в этом шуме потерялось бы."""
    repository = GenresRepository(sessions)
    with caplog.at_level(logging.WARNING):
        assert await repository.resolve(GenreSource.STEAM_TAG, ["19", "4106"]) == []
        assert await repository.resolve(GenreSource.GOG_TAG, ["atmospheric"]) == []
    assert caplog.text == ""


async def test_a_rejected_gog_slug_is_not_news(sessions, reference, caplog):
    """Шестнадцать слагов приезжают у GOG в поле `genres`, но жанрами не
    являются: камера, ход времени, эпоха и темы. Это известное и отвергнутое, а
    не незнакомое, и путать одно с другим нельзя — иначе правило перестанет
    ловить настоящее."""
    repository = GenresRepository(sessions)
    with caplog.at_level(logging.WARNING):
        assert await repository.resolve(GenreSource.GOG, ["fpp", "fantasy"]) == []
    assert caplog.text == ""


async def test_an_unknown_gog_slug_is_still_news(sessions, reference, caplog):
    """Обратная половина: словарь жанров у магазина закрытый, и незнакомый
    слаг означает, что магазин его расширил. Это стоит увидеть."""
    repository = GenresRepository(sessions)
    with caplog.at_level(logging.WARNING):
        await repository.resolve(GenreSource.GOG, ["совсем-новый-жанр"])
    assert "совсем-новый-жанр" in caplog.text


async def test_sources_do_not_leak_into_each_other(sessions, reference):
    # У Steam свой словарь: id 3 у него ролевая, а не драма.
    assert await GenresRepository(sessions).resolve(GenreSource.STEAM, ["3"]) == [4]
    assert await GenresRepository(sessions).resolve(GenreSource.TMDB, ["3"]) == []


async def test_set_and_read_genres_of_a_card(sessions, reference, card):
    item_id = await card()
    repository = GenresRepository(sessions)

    await repository.set_for_item(item_id, [3, 1])
    names = [genre.name for genre in await repository.genres_of(item_id)]
    # Порядок по названию, а не по тому, в каком пришли: сравнивается список,
    # а не множество — иначе обратная сортировка прошла бы молча.
    assert names == ["Боевик", "Драма"]


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
