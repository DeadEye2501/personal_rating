import pytest

from backend.model import (
    CardView,
    GenreSource,
    Kind,
    SearchHit,
    Source,
    merge_results,
    view_from_hit,
)
from backend.service.search import SEARCH_SIZE, SearchService
from backend.sources.errors import Found, Missing, Reason, Refusal
from backend.storage.repository.genres import GenresRepository
from backend.storage.repository.library import LibraryRepository
from backend.storage.repository.views import ViewsRepository
from tests.conftest import FakeClient, FakeSources, seed


class FakeCatalog(FakeClient):
    """Спрашивают у него только выдачу поиска. Заданное исключение он бросает, а
    не возвращает: сервис обязан пережить и это."""

    async def search(self, query: str, kind: Kind):
        self.asked.append((query, kind))
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


def hit(source_id="157336", title="Интерстеллар", source=Source.TMDB,
        kind=Kind.MOVIE, **fields) -> SearchHit:
    # `kind` — именованный параметр, а не жёсткое `Kind.MOVIE` внутри: иначе
    # вызов `hit(..., kind=Kind.GAME)` даёт «got multiple values for keyword
    # argument 'kind'».
    return SearchHit(kind=kind, source=source, source_id=source_id,
                     title=title, **fields)


def local_view(source_id="157336", title="Интерстеллар") -> CardView:
    return CardView(item_id=7, kind=Kind.MOVIE, source=Source.TMDB,
                    source_id=source_id, title=title)


def test_a_local_card_takes_the_place_of_its_external_twin():
    """Своё стоит на своём месте в общей выдаче и ничем не выделено."""
    external = [view_from_hit(hit("1", "Первый")), view_from_hit(hit("157336"))]
    merged = merge_results([local_view()], external)

    assert [v.source_id for v in merged] == ["1", "157336"]
    assert merged[1].item_id == 7


def test_what_is_found_only_locally_goes_to_the_end():
    external = [view_from_hit(hit("1", "Первый"))]
    merged = merge_results([local_view("999", "Только у меня")], external)

    assert [v.source_id for v in merged] == ["1", "999"]


def test_duplicates_inside_one_answer_are_dropped():
    external = [view_from_hit(hit("157336")), view_from_hit(hit("157336"))]

    assert len(merge_results([], external)) == 1


def test_the_same_game_in_two_stores_shows_up_twice():
    """Общего ключа между Steam и GOG нет — склейки в выдаче тоже. Решает
    человек.

    Идентификатор нарочно один и тот же: диапазоны номеров у магазинов
    пересекаются, и ключ обязан быть составным. При склейке по одному
    `source_id` одна из двух игр молча пропала бы."""
    external = [
        view_from_hit(hit("100", "The Witcher 3", source=Source.STEAM)),
        view_from_hit(hit("100", "The Witcher 3", source=Source.GOG)),
    ]

    assert len(merge_results([], external)) == 2


def test_a_local_card_of_another_source_does_not_take_the_place():
    """Тот же составной ключ с другой стороны: своя карточка из Steam не
    подменяет собой кандидата из GOG под тем же номером."""
    mine = CardView(item_id=7, kind=Kind.GAME, source=Source.STEAM,
                    source_id="100", title="Ведьмак у меня")
    external = [view_from_hit(hit("100", "Ведьмак в GOG", source=Source.GOG,
                                  kind=Kind.GAME))]

    merged = merge_results([mine], external)

    assert [v.title for v in merged] == ["Ведьмак в GOG", "Ведьмак у меня"]


def test_order_of_the_source_is_kept():
    external = [view_from_hit(hit(str(n), f"Фильм {n}")) for n in range(5)]
    merged = merge_results([], external)

    assert [v.source_id for v in merged] == ["0", "1", "2", "3", "4"]


def test_nothing_found_anywhere_is_an_empty_answer():
    assert merge_results([], []) == []


@pytest.fixture
async def service(sessions):
    def build(*clients) -> SearchService:
        return SearchService(LibraryRepository(sessions),
                            ViewsRepository(sessions),
                            FakeSources(*clients),
                            GenresRepository(sessions))
    return build


async def test_the_external_answer_becomes_candidates(sessions, service):
    search = service(FakeCatalog(Found([hit()])))

    result = await search.external(Kind.MOVIE, "интерстеллар")

    assert [v.title for v in result.views] == ["Интерстеллар"]
    assert result.views[0].item_id is None
    assert result.refusals == ()


async def test_the_query_and_the_kind_reach_the_source(sessions, service):
    """Что спросили снаружи, то и уехало в источник: подмена типа содержимого
    молча дала бы выдачу не того раздела."""
    client = FakeCatalog(Found([hit()]))

    await service(client).external(Kind.SERIES, "андор")

    assert client.asked == [("андор", Kind.SERIES)]


async def test_genres_are_unfolded_from_the_reference(sessions, reference, service):
    """В выдаче приходят голые идентификаторы: 18 — это драма."""
    search = service(FakeCatalog(
        Found([hit(genre_ext_ids=((GenreSource.TMDB, "18"),))])
    ))

    result = await search.external(Kind.MOVIE, "интерстеллар")

    assert [g.name for g in result.views[0].genres] == ["Драма"]


async def test_a_compound_genre_unfolds_into_two(sessions, reference, service):
    """У TMDB в сериалах «Боевик и приключения» — это не жанр, а два.

    Сверяем состав, а не длину: два неверных жанра прошли бы проверку длины."""
    search = service(FakeCatalog(
        Found([hit(genre_ext_ids=((GenreSource.TMDB, "10759"),))])
    ))

    result = await search.external(Kind.SERIES, "andor")

    assert [g.name for g in result.views[0].genres] == ["Боевик", "Приключения"]


async def test_overlapping_identifiers_do_not_duplicate_a_genre(
    sessions, reference, service
):
    """Сборный 10759 и обычный 28 оба дают Боевик — жанр должен быть один."""
    search = service(FakeCatalog(Found([hit(genre_ext_ids=(
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
    search = service(FakeCatalog(
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
    search = service(FakeCatalog(
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
    search = service(FakeCatalog(Found([hit(
        "292030", "Ведьмак", source=Source.STEAM, kind=Kind.GAME,
        genre_ext_ids=((GenreSource.STEAM, "9"), (GenreSource.STEAM_TAG, "9")),
    )]), name="steam"))

    result = await search.external(Kind.GAME, "ведьмак")

    assert [g.name for g in result.views[0].genres] == ["гонки", "ролевая"]


async def test_a_candidate_without_genres_brings_none(sessions, service):
    """В выдаче магазинов жанров не бывает вовсе — только в карточке. Пустой
    список не должен превращаться ни в отказ, ни в выдуманный жанр."""
    search = service(FakeCatalog(Found([hit()])))

    result = await search.external(Kind.MOVIE, "интерстеллар")

    assert result.views[0].genres == ()


async def test_an_unknown_genre_is_dropped_without_a_word(
    sessions, reference, service, caplog
):
    """Справочник нарочно засеян: с пустым `genre_map` неизвестен любой
    идентификатор, и тест был бы зелёным даже при сломанном разборе."""
    search = service(FakeCatalog(Found([hit(genre_ext_ids=(
        (GenreSource.TMDB, "18"), (GenreSource.TMDB, "99999"),
    ))])))

    with caplog.at_level("DEBUG"):
        result = await search.external(Kind.MOVIE, "интерстеллар")

    assert [g.name for g in result.views[0].genres] == ["Драма"]
    assert [r for r in caplog.records if r.name.startswith("backend")] == []


async def test_a_refusal_is_reported_and_not_raised(sessions, service):
    """Отказ источника — состояние данных, а не ошибка."""
    refusal = Refusal(source="tmdb", reason=Reason.NETWORK)
    search = service(FakeCatalog(refusal))

    result = await search.external(Kind.MOVIE, "интерстеллар")

    assert result.views == ()
    assert result.refusals == (refusal,)


async def test_a_broken_client_becomes_a_refusal_with_its_name(
    sessions, service, caplog
):
    """Сорвавшийся клиент — тоже отказ, а не исключение наружу: у границы
    потоков второго канала доставки нет. В отказе стоит имя источника, а не
    repr клиента: его увидит человек в плашке."""
    search = service(FakeCatalog(RuntimeError("разбор не удался"), name="steam"))

    with caplog.at_level("ERROR"):
        result = await search.external(Kind.GAME, "ведьмак")

    assert result.views == ()
    assert (result.refusals[0].source, result.refusals[0].reason) == (
        "steam", Reason.BROKEN
    )
    assert "разбор не удался" in result.refusals[0].detail
    assert [r for r in caplog.records if r.name.startswith("backend")] != []


async def test_a_broken_client_does_not_hide_the_other(sessions, service):
    """Второй магазин отвечает своё, и его находки доезжают."""
    broken = FakeCatalog(RuntimeError("сорвался"), name="steam")
    gog = FakeCatalog(Found([hit("1207664663", "Ведьмак", source=Source.GOG)]),
                      name="gog")

    result = await service(broken, gog).external(Kind.GAME, "ведьмак")

    assert [v.title for v in result.views] == ["Ведьмак"]
    assert [r.source for r in result.refusals] == ["steam"]


async def test_an_empty_answer_is_not_a_refusal(sessions, service):
    """Внешняя база ответила и ничего не нашла — сообщать не о чем."""
    search = service(FakeCatalog(Found([])))

    result = await search.external(Kind.MOVIE, "ничего такого")

    assert (result.views, result.refusals) == ((), ())


async def test_a_missing_answer_is_not_a_refusal_either(sessions, service):
    search = service(FakeCatalog(Missing()))

    result = await search.external(Kind.MOVIE, "ничего такого")

    assert (result.views, result.refusals) == ((), ())


async def test_two_stores_are_asked_at_once(sessions, service):
    """У игр кандидатов спрашивают у двух магазинов сразу — и с тем же запросом
    и типом, что пришли снаружи."""
    steam = FakeCatalog(Found([hit("292030", "Ведьмак", source=Source.STEAM)]),
                        name="steam")
    gog = FakeCatalog(Found([hit("1207664663", "Ведьмак", source=Source.GOG)]),
                      name="gog")

    result = await service(steam, gog).external(Kind.GAME, "ведьмак")

    assert len(result.views) == 2
    assert steam.asked == [("ведьмак", Kind.GAME)]
    assert gog.asked == [("ведьмак", Kind.GAME)]


async def test_two_stores_come_woven_and_not_in_blocks(sessions, service):
    """Спека требует «показывают вперемешку». Подряд это значит, что вторая
    половина страницы — всегда GOG, а он на бессмыслицу отдаёт два десятка
    несвязанных игр: настоящие находки уехали бы за экран."""
    steam = FakeCatalog(Found([hit(f"s{n}", f"Steam {n}", source=Source.STEAM)
                               for n in range(3)]), name="steam")
    gog = FakeCatalog(Found([hit(f"g{n}", f"GOG {n}", source=Source.GOG)
                             for n in range(3)]), name="gog")

    result = await service(steam, gog).external(Kind.GAME, "ведьмак")

    assert [v.source_id for v in result.views] == [
        "s0", "g0", "s1", "g1", "s2", "g2"
    ]


async def test_a_shorter_answer_does_not_leave_a_hole(sessions, service):
    """Магазины отдают разное число находок — переплетение это переживает."""
    steam = FakeCatalog(Found([hit(f"s{n}", f"Steam {n}", source=Source.STEAM)
                               for n in range(3)]), name="steam")
    gog = FakeCatalog(Found([hit("g0", "GOG 0", source=Source.GOG)]), name="gog")

    result = await service(steam, gog).external(Kind.GAME, "ведьмак")

    assert [v.source_id for v in result.views] == ["s0", "g0", "s1", "s2"]


async def test_one_source_keeps_the_order_it_gave(sessions, service):
    """У кино источник один, и переплетать нечего: порядок TMDB как есть."""
    search = service(FakeCatalog(Found([hit(str(n), f"Фильм {n}")
                                        for n in range(5)])))

    result = await search.external(Kind.MOVIE, "фильм")

    assert [v.source_id for v in result.views] == ["0", "1", "2", "3", "4"]


async def test_one_store_refusing_does_not_hide_the_other(sessions, service):
    steam = FakeCatalog(Refusal(source="steam", reason=Reason.NETWORK),
                        name="steam")
    gog = FakeCatalog(Found([hit("1207664663", "Ведьмак", source=Source.GOG)]),
                      name="gog")

    result = await service(steam, gog).external(Kind.GAME, "ведьмак")

    assert len(result.views) == 1
    assert len(result.refusals) == 1


async def test_both_stores_refusing_report_both(sessions, service):
    """Ранний выход после первого отказа оставил бы человека без половины
    объяснения: плашка перечисляет всех, кто не ответил."""
    steam = FakeCatalog(Refusal(source="steam", reason=Reason.NETWORK),
                        name="steam")
    gog = FakeCatalog(Refusal(source="gog", reason=Reason.RATE), name="gog")

    result = await service(steam, gog).external(Kind.GAME, "ведьмак")

    assert result.views == ()
    assert sorted(r.source for r in result.refusals) == ["gog", "steam"]


async def test_a_portion_is_counted_per_source_and_not_per_page(sessions, service):
    """У игр магазина два, и по 20 у каждого — это два запроса, как и сказано в
    спеке. Срез на общей выдаче отдал бы 20 на двоих."""
    steam = FakeCatalog(Found([hit(f"s{n}", f"Steam {n}", source=Source.STEAM)
                               for n in range(50)]), name="steam")
    gog = FakeCatalog(Found([hit(f"g{n}", f"GOG {n}", source=Source.GOG)
                             for n in range(50)]), name="gog")

    result = await service(steam, gog).external(Kind.GAME, "ведьмак")

    assert len(result.views) == 2 * SEARCH_SIZE


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
    steam = FakeCatalog(Found([
        hit(f"s{n}", source=Source.STEAM, kind=Kind.GAME,
            genre_ext_ids=((GenreSource.STEAM, "3"),))
        for n in range(5)
    ]), name="steam")
    gog = FakeCatalog(Found([
        hit(f"g{n}", source=Source.GOG, kind=Kind.GAME,
            genre_ext_ids=((GenreSource.GOG, "role-playing"),))
        for n in range(5)
    ]), name="gog")

    await service(steam, gog).external(Kind.GAME, "ведьмак")

    assert asked == [GenreSource.STEAM, GenreSource.GOG]
