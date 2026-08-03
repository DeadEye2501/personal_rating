"""Жанры кандидата: чужие метки разворачиваются нашим справочником.

Отделено от проверок выдачи, когда та упёрлась в предел файла: шов прошёл
здесь, потому что справочник — отдельное дело, и о самой выдаче эти девять
проверок не говорят ничего."""


from backend.model import Found, GenreSource, Kind, Source
from backend.storage.repository.genres import GenresRepository
from tests.conftest import FakeSearch, hit, seed




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
    """Порядок задаёт справочник, а не порядок правил в нём: жанры стоят в
    карточке в ряд, и перетасовываться между показами им нельзя.

    Правила заведены свои, и пара выбрана так, что алфавит обратен порядку
    номеров: «Приключения» — это 2, «Драма» — 3. У сборного `10759` из общего
    набора они совпадают, и потеря сортировки прошла бы там молча."""
    await seed(
        engine,
        "INSERT INTO genre_rule (id, source, genre_id, alone) VALUES "
        "(10, 'tmdb', 2, 0), (11, 'tmdb', 3, 0)",
        "INSERT INTO genre_rule_mark (rule_id, ext_id, forbidden) VALUES "
        "(10, '99', 0), (11, '99', 0)",
    )
    search = service(FakeSearch(
        Found([hit(genre_ext_ids=((GenreSource.TMDB, "99"),))])
    ))

    result = await search.external(Kind.MOVIE, "интерстеллар")

    assert [g.name for g in result.views[0].genres] == ["Драма", "Приключения"]

async def test_the_marks_of_a_candidate_are_read_by_the_rules(sessions, engine,
                                                              reference, service):
    """В выдаче жанры разворачиваются теми же правилами, что и в карточке:
    метка сама по себе жанра не означает, и поштучный перевод показал бы
    кандидату жанр, которого у него нет."""
    await seed(
        engine,
        "INSERT INTO genre (id, name, kind) VALUES (5, 'гонки', 'game')",
        "INSERT INTO genre_rule (id, source, genre_id, alone) VALUES "
        "(10, 'steam', 5, 0)",
        "INSERT INTO genre_rule_mark (rule_id, ext_id, forbidden) VALUES "
        "(10, '9', 0), (10, '3', 1)",
    )
    search = service(FakeSearch(Found([hit(
        "292030", "Ведьмак", source=Source.STEAM, kind=Kind.GAME,
        genre_ext_ids=((GenreSource.STEAM, "9"), (GenreSource.STEAM, "3")),
    )]), name="steam"))

    result = await search.external(Kind.GAME, "ведьмак")

    assert [g.name for g in result.views[0].genres] == ["ролевая"]

async def test_a_candidate_without_genres_brings_none(sessions, service):
    """В выдаче магазинов жанров не бывает вовсе — только в карточке. Пустой
    список не должен превращаться ни в отказ, ни в выдуманный жанр."""
    search = service(FakeSearch(Found([hit()])))

    result = await search.external(Kind.MOVIE, "интерстеллар")

    assert result.views[0].genres == ()

async def test_an_unknown_genre_is_dropped_without_a_word(
    sessions, reference, service, caplog
):
    """Справочник нарочно засеян: с пустым справочником неизвестна любая
    метка, и тест был бы зелёным даже при сломанном разборе."""
    search = service(FakeSearch(Found([hit(genre_ext_ids=(
        (GenreSource.TMDB, "18"), (GenreSource.TMDB, "99999"),
    ))])))

    with caplog.at_level("DEBUG"):
        result = await search.external(Kind.MOVIE, "интерстеллар")

    assert [g.name for g in result.views[0].genres] == ["Драма"]
    assert [r for r in caplog.records if r.name.startswith("backend")] == []

async def test_the_reference_is_asked_once_per_space(sessions, reference, service,
                                                     monkeypatch):
    """Спрашивать правила по кандидату значит запрос на кандидата. Но и один
    набор на всех не годится: метки GOG развернулись бы правилами Steam."""
    asked = []
    original = GenresRepository.rules

    async def counting(self, source):
        asked.append(source)
        return await original(self, source)

    monkeypatch.setattr(GenresRepository, "rules", counting)
    # Названия у всех разные: одинаковые склеились бы в одну строку — по
    # решению задачи 5 это одна игра, — и до второго пространства выдача бы не
    # дошла. Предмет проверки тут другой, и путать его со склейкой незачем.
    steam = FakeSearch(Found([
        hit(f"s{n}", f"Игра Steam {n}", source=Source.STEAM, kind=Kind.GAME,
            genre_ext_ids=((GenreSource.STEAM, "3"),))
        for n in range(5)
    ]), name="steam")
    gog = FakeSearch(Found([
        hit(f"g{n}", f"Игра GOG {n}", source=Source.GOG, kind=Kind.GAME,
            genre_ext_ids=((GenreSource.GOG, "rpg"),))
        for n in range(5)
    ]), name="gog")

    await service(steam, gog).external(Kind.GAME, "ведьмак")

    assert asked == [GenreSource.STEAM, GenreSource.GOG]
