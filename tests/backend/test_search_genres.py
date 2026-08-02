"""Жанры кандидата: чужие метки разворачиваются нашим справочником.

Отделено от проверок выдачи, когда та упёрлась в предел файла: шов прошёл
здесь, потому что справочник — отдельное дело, и о самой выдаче эти девять
проверок не говорят ничего."""

import pytest

from backend.model import Found, GenreSource, Kind, Source
from backend.storage.repository.genres import GenresRepository
from tests.conftest import FakeSearch, hit, seed
from tests.wiring import search_service


@pytest.fixture
async def service(sessions):
    return lambda *clients: search_service(sessions, *clients)


async def test_genres_are_unfolded_from_the_reference(sessions, reference, service):
    """В выдаче приходят голые идентификаторы: 18 — это драма."""
    search = service(FakeSearch(
        Found([hit(genre_ext_ids=((GenreSource.TMDB, "18"),))])
    ))

    result = await search.external(Kind.MOVIE, "интерстеллар")

    assert [g.name for g in result.views[0].genres] == ["Драма"]

async def test_a_compound_genre_unfolds_into_two(sessions, reference, service):
    """У TMDB в сериалах «Боевик и приключения» — это не жанр, а два.

    Сверяем состав, а не длину: два неверных жанра прошли бы проверку длины."""
    search = service(FakeSearch(
        Found([hit(genre_ext_ids=((GenreSource.TMDB, "10759"),))])
    ))

    result = await search.external(Kind.SERIES, "andor")

    assert [g.name for g in result.views[0].genres] == ["Боевик", "Приключения"]

async def test_overlapping_identifiers_do_not_duplicate_a_genre(
    sessions, reference, service
):
    """Сборный 10759 и обычный 28 оба дают Боевик — жанр должен быть один."""
    search = service(FakeSearch(Found([hit(genre_ext_ids=(
        (GenreSource.TMDB, "10759"), (GenreSource.TMDB, "28"),
    ))])))

    result = await search.external(Kind.SERIES, "andor")

    assert [g.name for g in result.views[0].genres] == ["Боевик", "Приключения"]

async def test_the_spaces_of_genres_do_not_leak_into_each_other(
    sessions, reference, service
):
    """У магазина и у TMDB нумерация своя: `3` у Steam — это «ролевая», а у
    TMDB такого номера нет вовсе. Спроси справочник без отбора по пространству,
    и кино получило бы игровой жанр."""
    search = service(FakeSearch(
        Found([hit(genre_ext_ids=((GenreSource.TMDB, "3"),))])
    ))

    result = await search.external(Kind.MOVIE, "интерстеллар")

    assert result.views[0].genres == ()

async def test_a_compound_genre_comes_in_the_order_of_the_alphabet(
    sessions, engine, reference, service
):
    """Порядок задаёт справочник, а не порядок строк в нём: жанры стоят в
    карточке в ряд, и перетасовываться между показами им нельзя.

    Соответствие заведено своё, и пара выбрана так, что алфавит обратен
    порядку номеров: «Приключения» — это 2, «Драма» — 3. У сборного `10759` из
    общего набора они совпадают, и потеря сортировки прошла бы там молча."""
    await seed(
        engine,
        "INSERT INTO genre_map (source, ext_id, genre_id) VALUES "
        "('tmdb', '99', 2), ('tmdb', '99', 3)",
    )
    search = service(FakeSearch(
        Found([hit(genre_ext_ids=((GenreSource.TMDB, "99"),))])
    ))

    result = await search.external(Kind.MOVIE, "интерстеллар")

    assert [g.name for g in result.views[0].genres] == ["Драма", "Приключения"]

async def test_a_tag_and_a_genre_of_one_store_do_not_mix(sessions, engine,
                                                         reference, service):
    """У Steam жанр и тег нумеруются порознь: `9` — это жанр «гонки» и тег
    «ролевая» одновременно. Ключом словаря обязано быть пространство, а не
    источник карточки: иначе стратегии получили бы гонки."""
    await seed(
        engine,
        "INSERT INTO genre (id, name, kind) VALUES (5, 'гонки', 'game')",
        "INSERT INTO genre_map (source, ext_id, genre_id) VALUES "
        "('steam', '9', 5), ('steam_tag', '9', 4)",
    )
    search = service(FakeSearch(Found([hit(
        "292030", "Ведьмак", source=Source.STEAM, kind=Kind.GAME,
        genre_ext_ids=((GenreSource.STEAM, "9"), (GenreSource.STEAM_TAG, "9")),
    )]), name="steam"))

    result = await search.external(Kind.GAME, "ведьмак")

    assert [g.name for g in result.views[0].genres] == ["гонки", "ролевая"]

async def test_a_candidate_without_genres_brings_none(sessions, service):
    """В выдаче магазинов жанров не бывает вовсе — только в карточке. Пустой
    список не должен превращаться ни в отказ, ни в выдуманный жанр."""
    search = service(FakeSearch(Found([hit()])))

    result = await search.external(Kind.MOVIE, "интерстеллар")

    assert result.views[0].genres == ()

async def test_an_unknown_genre_is_dropped_without_a_word(
    sessions, reference, service, caplog
):
    """Справочник нарочно засеян: с пустым `genre_map` неизвестен любой
    идентификатор, и тест был бы зелёным даже при сломанном разборе."""
    search = service(FakeSearch(Found([hit(genre_ext_ids=(
        (GenreSource.TMDB, "18"), (GenreSource.TMDB, "99999"),
    ))])))

    with caplog.at_level("DEBUG"):
        result = await search.external(Kind.MOVIE, "интерстеллар")

    assert [g.name for g in result.views[0].genres] == ["Драма"]
    assert [r for r in caplog.records if r.name.startswith("backend")] == []

async def test_the_reference_is_asked_once_per_space(sessions, reference, service,
                                                     monkeypatch):
    """Разворачивать жанры по кандидату значит запрос на кандидата. Но и один
    словарь на всех не годится: жанры GOG развернулись бы по словарю Steam."""
    asked = []
    original = GenresRepository.index

    async def counting(self, source):
        asked.append(source)
        return await original(self, source)

    monkeypatch.setattr(GenresRepository, "index", counting)
    steam = FakeSearch(Found([
        hit(f"s{n}", source=Source.STEAM, kind=Kind.GAME,
            genre_ext_ids=((GenreSource.STEAM, "3"),))
        for n in range(5)
    ]), name="steam")
    gog = FakeSearch(Found([
        hit(f"g{n}", source=Source.GOG, kind=Kind.GAME,
            genre_ext_ids=((GenreSource.GOG, "role-playing"),))
        for n in range(5)
    ]), name="gog")

    await service(steam, gog).external(Kind.GAME, "ведьмак")

    assert asked == [GenreSource.STEAM, GenreSource.GOG]
