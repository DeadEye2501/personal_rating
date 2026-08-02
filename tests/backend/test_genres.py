"""Жанры карточки в базе: чтение справочника и запись набора.

Как метки превращаются в жанры — `test_genre_rules.py` и
`test_genre_resolution.py`; здесь только то, что делает сам репозиторий."""

import pytest


from backend.model import Dangling, GenreKind, GenreSource, Kind
from backend.service.genres import matched
from backend.storage.repository.genres import GenresRepository


async def test_a_rule_comes_back_with_the_genre_it_leads_to(sessions, reference):
    """Наружу репозиторий отдаёт правила, а не строки: жанр в них уже собран,
    и второго запроса за именем не нужно."""
    rules = await GenresRepository(sessions).rules(GenreSource.TMDB)

    assert [genre.name for genre in matched(rules, {"18"})] == ["Драма"]


async def test_one_mark_leads_to_two_genres_by_two_rules(sessions, reference):
    """Сборный жанр TMDB — это два правила с одной меткой, а не правило с двумя
    жанрами."""
    rules = await GenresRepository(sessions).rules(GenreSource.TMDB)

    assert sorted(genre.id for genre in matched(rules, {"10759"})) == [1, 2]


async def test_the_rules_of_one_source_do_not_include_another(sessions, reference):
    """Отбор по источнику: `3` у Steam — это ролевая, а у TMDB такой метки нет
    вовсе. Спроси репозиторий без отбора — кино получило бы игровой жанр."""
    steam = await GenresRepository(sessions).rules(GenreSource.STEAM)
    tmdb = await GenresRepository(sessions).rules(GenreSource.TMDB)

    assert [genre.id for genre in matched(steam, {"3"})] == [4]
    assert matched(tmdb, {"3"}) == []


async def test_a_source_without_rules_gives_an_empty_book(sessions, reference):
    """У пространства без единого правила справочник пуст, а не сломан:
    old-games.ru появится в базе раньше, чем его клиент."""
    assert await GenresRepository(sessions).rules(GenreSource.OLD_GAMES) == ()


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


async def test_a_failed_replacement_keeps_the_old_set(sessions, reference, card):
    """Замена набора — это очистка плюс вставка, и обе обязаны быть одной
    транзакцией. Сорвись вставка на полпути — карточка осталась бы без жанров
    вовсе, и починить это могла бы только новая загрузка из источника.

    Срыв здесь настоящий: номер жанра, которого в справочнике нет, роняет
    внешний ключ уже после очистки."""
    item_id = await card()
    repository = GenresRepository(sessions)
    await repository.set_for_item(item_id, [3])
    before = [one.id for one in await repository.genres_of(item_id)]
    assert before, "фикстура пуста — проверять нечего"

    # Ловим именно сорванную ссылку: широкий `Exception` провёл бы тест зелёным
    # и на опечатке в нём самом, не дойдя до проверяемого места. `IntegrityError`
    # сюда больше не долетает — репозиторий переводит его в свой отказ, чтобы
    # знание о SQLAlchemy не ехало вверх по слоям.
    with pytest.raises(Dangling):
        await repository.set_for_item(item_id, [999999])

    assert [one.id for one in await repository.genres_of(item_id)] == before
