"""Поиск по чужим базам: выдача, отказы и переплетение выдач — как двух
магазинов, так и двух половин одного источника.

Складывание своей выдачи с чужой — у `merge_results`, в своём модуле: оно живёт
в модели и зовётся ещё и с той стороны границы, мостом."""

import pytest

from backend.model import (
    Found,
    GenreSource,
    Kind,
    Missing,
    PersonHit,
    RatingSource,
    Reason,
    Refusal,
    Source,
)
from backend.service.search import SEARCH_SIZE, SearchService
from backend.storage.repository.genres import GenresRepository
from backend.storage.repository.library import LibraryRepository
from backend.storage.repository.views import ViewsRepository
from tests.conftest import MOMENT, FakeSearch, FakeSources, hit, seed


@pytest.fixture
async def service(sessions):
    def build(*clients) -> SearchService:
        return SearchService(LibraryRepository(sessions),
                            ViewsRepository(sessions),
                            FakeSources(*clients),
                            GenresRepository(sessions),
                            clock=lambda: MOMENT)
    return build


async def test_the_external_answer_becomes_candidates(sessions, service):
    search = service(FakeSearch(Found([hit()])))

    result = await search.external(Kind.MOVIE, "интерстеллар")

    assert [v.title for v in result.views] == ["Интерстеллар"]
    assert result.views[0].item_id is None
    assert result.refusals == ()


async def test_the_free_rating_reaches_the_candidate(sessions, service):
    """Оценка приезжает даром вместе с выдачей, и до карточки она обязана
    доехать: собирает её `sources/convert.py`, а сервис только передаёт — потеряй
    он этот вызов, кандидаты показывались бы без оценки источника, и заметить это
    было бы негде.

    Отметка времени берётся у внедрённых часов, а не у настоящих: своё время
    внутри модели однажды уехало бы в базу непроверяемым."""
    search = service(FakeSearch(Found([hit(source_rating=8.4)])))

    result = await search.external(Kind.MOVIE, "интерстеллар")

    external = result.views[0].external
    assert [(r.source, r.value, r.fetched_at) for r in external] == [
        (RatingSource.TMDB, 8.4, MOMENT)
    ]


async def test_the_query_and_the_kind_reach_both_halves(sessions, service):
    """Что спросили снаружи, то и уехало в источник: подмена типа содержимого
    молча дала бы выдачу не того раздела.

    Обе половины, а не только названия: вкладка — первичный фильтр и для работ
    человека, иначе клик по вкладке фильмов привёз бы его сериалы."""
    client = FakeSearch(Found([hit()]), people=Found([PersonHit("525")]),
                        works=Found([]))

    await service(client).external(Kind.SERIES, "андор")

    # Набор целиком и его длина, а не членство: лишний вопрос — повторный
    # запрос к каталогу или фильмография того, кого не находили — прошёл бы
    # молча. Порядком половины не связаны: они уходят разом.
    assert len(client.asked) == 3
    assert set(client.asked) == {
        ("андор", Kind.SERIES),
        ("find_people", "андор"),
        ("credits_of", "525", Kind.SERIES),
    }


async def test_a_name_in_the_query_brings_the_works_of_that_person(sessions,
                                                                   service):
    """Строка ищет и по имени — всегда, а не «если названием ничего не
    нашлось»: решение пользователя 01.08.2026. До него «Джон Траволта» не
    находил снаружи ничего вовсе."""
    client = FakeSearch(Found([]), people=Found([PersonHit("8891")]),
                        works=Found([hit("680", "Криминальное чтиво")]))

    result = await service(client).external(Kind.MOVIE, "джон траволта")

    assert [v.title for v in result.views] == ["Криминальное чтиво"]


async def test_titles_and_people_come_woven(sessions, service):
    """Тем же переплетением, что и два магазина: подряд это значит, что
    фильмография одного актёра вытеснит всё найденное по названию — у неё две
    сотни строк, а порция одна."""
    client = FakeSearch(
        Found([hit(f"t{n}", f"Название {n}") for n in range(2)]),
        people=Found([PersonHit("8891")]),
        works=Found([hit(f"p{n}", f"Работа {n}") for n in range(2)]),
    )

    result = await service(client).external(Kind.MOVIE, "траволта")

    assert [v.source_id for v in result.views] == ["t0", "p0", "t1", "p1"]


async def test_the_filmography_is_cut_to_the_portion_too(sessions, service):
    """Порция считается по выдаче, и половина людей не исключение: работ у
    тёзок бывают сотни, а показанная строка ложится в базу.

    Тёзки нарочно двое: с одним срез, уехавший внутрь запроса по человеку, лёг
    бы на каждого порознь и остался бы незамеченным — двое дали бы сорок
    строк."""
    client = FakeSearch(Found([]),
                        people=Found([PersonHit("1"), PersonHit("2")]),
                        works={"1": Found([hit(f"a{n}") for n in range(15)]),
                               "2": Found([hit(f"b{n}") for n in range(15)])})

    result = await service(client).external(Kind.MOVIE, "траволта")

    assert len(result.views) == SEARCH_SIZE


async def test_a_refusal_of_the_name_search_travels_as_a_refusal(sessions,
                                                                 service):
    """Отказ половины людей — поле в результате, а не исключение: у границы
    потоков второго канала доставки нет. Найденное по названию при этом
    доезжает."""
    client = FakeSearch(Found([hit()]),
                        people=Refusal(source="tmdb", reason=Reason.NETWORK))

    result = await service(client).external(Kind.MOVIE, "траволта")

    assert [v.title for v in result.views] == ["Интерстеллар"]
    assert [r.reason for r in result.refusals] == [Reason.NETWORK]


async def test_one_source_refusing_both_halves_says_so_once(sessions, service):
    """Обе половины строки спрашивают один TMDB, и легла сеть — плашка внизу
    говорит про источник, а он тут один.

    Отказы нарочно разные подробностью: в жизни они и расходятся — первый же
    сбой взводит предохранитель, и вторая половина возвращает уже его. Сверка
    целиком показала бы один TMDB двумя строками."""
    client = FakeSearch(
        Refusal(source="tmdb", reason=Reason.NETWORK, detail="не дозвонились"),
        people=Refusal(source="tmdb", reason=Reason.NETWORK,
                       detail="предохранитель взведён"),
    )

    result = await service(client).external(Kind.MOVIE, "траволта")

    assert [(r.source, r.reason) for r in result.refusals] == [
        ("tmdb", Reason.NETWORK)
    ]


async def test_two_stores_down_by_the_same_reason_stay_two(sessions, service):
    """Схлопывание идёт по паре «источник и причина», а не по одной причине, и
    это самый частый случай из всех: сеть легла — оба магазина отвечают одним и
    тем же. Потеряй ключ источник, GOG исчез бы из плашки."""
    steam = FakeSearch(Refusal(source="steam", reason=Reason.NETWORK),
                       name="steam")
    gog = FakeSearch(Refusal(source="gog", reason=Reason.NETWORK), name="gog")

    result = await service(steam, gog).external(Kind.GAME, "ведьмак")

    assert sorted(r.source for r in result.refusals) == ["gog", "steam"]


async def test_games_never_go_outside_for_people(sessions, service):
    """Кого спрашивать про людей — решает реестр, и сервис обязан его
    слушаться: у игр такого клиента нет вовсе."""
    client = FakeSearch(Found([]), people=Found([PersonHit("1")]), name="steam")

    await service(client).external(Kind.GAME, "ведьмак")

    assert [one for one in client.asked if one[0] == "find_people"] == []


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


async def test_a_refusal_is_reported_and_not_raised(sessions, service):
    """Отказ источника — состояние данных, а не ошибка."""
    refusal = Refusal(source="tmdb", reason=Reason.NETWORK)
    search = service(FakeSearch(refusal))

    result = await search.external(Kind.MOVIE, "интерстеллар")

    assert result.views == ()
    assert result.refusals == (refusal,)


async def test_a_broken_client_becomes_a_refusal_with_its_name(
    sessions, service, caplog
):
    """Сорвавшийся клиент — тоже отказ, а не исключение наружу: у границы
    потоков второго канала доставки нет. В отказе стоит имя источника, а не
    repr клиента: его увидит человек в плашке."""
    search = service(FakeSearch(RuntimeError("разбор не удался"), name="steam"))

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
    broken = FakeSearch(RuntimeError("сорвался"), name="steam")
    gog = FakeSearch(Found([hit("1207664663", "Ведьмак", source=Source.GOG)]),
                      name="gog")

    result = await service(broken, gog).external(Kind.GAME, "ведьмак")

    assert [v.title for v in result.views] == ["Ведьмак"]
    assert [r.source for r in result.refusals] == ["steam"]


async def test_an_empty_answer_is_not_a_refusal(sessions, service):
    """Внешняя база ответила и ничего не нашла — сообщать не о чем."""
    search = service(FakeSearch(Found([])))

    result = await search.external(Kind.MOVIE, "ничего такого")

    assert (result.views, result.refusals) == ((), ())


async def test_a_missing_answer_is_not_a_refusal_either(sessions, service):
    search = service(FakeSearch(Missing()))

    result = await search.external(Kind.MOVIE, "ничего такого")

    assert (result.views, result.refusals) == ((), ())


async def test_two_stores_are_asked_at_once(sessions, service):
    """У игр кандидатов спрашивают у двух магазинов сразу — и с тем же запросом
    и типом, что пришли снаружи."""
    steam = FakeSearch(Found([hit("292030", "Ведьмак", source=Source.STEAM)]),
                        name="steam")
    gog = FakeSearch(Found([hit("1207664663", "Ведьмак", source=Source.GOG)]),
                      name="gog")

    result = await service(steam, gog).external(Kind.GAME, "ведьмак")

    assert len(result.views) == 2
    assert steam.asked == [("ведьмак", Kind.GAME)]
    assert gog.asked == [("ведьмак", Kind.GAME)]


async def test_two_stores_come_woven_and_not_in_blocks(sessions, service):
    """Спека требует «показывают вперемешку». Подряд это значит, что вторая
    половина страницы — всегда GOG, а он на бессмыслицу отдаёт два десятка
    несвязанных игр: настоящие находки уехали бы за экран."""
    steam = FakeSearch(Found([hit(f"s{n}", f"Steam {n}", source=Source.STEAM)
                               for n in range(3)]), name="steam")
    gog = FakeSearch(Found([hit(f"g{n}", f"GOG {n}", source=Source.GOG)
                             for n in range(3)]), name="gog")

    result = await service(steam, gog).external(Kind.GAME, "ведьмак")

    assert [v.source_id for v in result.views] == [
        "s0", "g0", "s1", "g1", "s2", "g2"
    ]


async def test_a_shorter_answer_does_not_leave_a_hole(sessions, service):
    """Магазины отдают разное число находок — переплетение это переживает."""
    steam = FakeSearch(Found([hit(f"s{n}", f"Steam {n}", source=Source.STEAM)
                               for n in range(3)]), name="steam")
    gog = FakeSearch(Found([hit("g0", "GOG 0", source=Source.GOG)]), name="gog")

    result = await service(steam, gog).external(Kind.GAME, "ведьмак")

    assert [v.source_id for v in result.views] == ["s0", "g0", "s1", "s2"]


async def test_one_source_keeps_the_order_it_gave(sessions, service):
    """У кино источник один, и переплетать нечего: порядок TMDB как есть."""
    search = service(FakeSearch(Found([hit(str(n), f"Фильм {n}")
                                        for n in range(5)])))

    result = await search.external(Kind.MOVIE, "фильм")

    assert [v.source_id for v in result.views] == ["0", "1", "2", "3", "4"]


async def test_one_store_refusing_does_not_hide_the_other(sessions, service):
    steam = FakeSearch(Refusal(source="steam", reason=Reason.NETWORK),
                        name="steam")
    gog = FakeSearch(Found([hit("1207664663", "Ведьмак", source=Source.GOG)]),
                      name="gog")

    result = await service(steam, gog).external(Kind.GAME, "ведьмак")

    assert len(result.views) == 1
    assert len(result.refusals) == 1


async def test_both_stores_refusing_report_both(sessions, service):
    """Ранний выход после первого отказа оставил бы человека без половины
    объяснения: плашка перечисляет всех, кто не ответил."""
    steam = FakeSearch(Refusal(source="steam", reason=Reason.NETWORK),
                        name="steam")
    gog = FakeSearch(Refusal(source="gog", reason=Reason.RATE), name="gog")

    result = await service(steam, gog).external(Kind.GAME, "ведьмак")

    assert result.views == ()
    assert sorted(r.source for r in result.refusals) == ["gog", "steam"]


async def test_a_portion_is_counted_per_source_and_not_per_page(sessions, service):
    """У игр магазина два, и по 20 у каждого — это два запроса, как и сказано в
    спеке. Срез на общей выдаче отдал бы 20 на двоих."""
    steam = FakeSearch(Found([hit(f"s{n}", f"Steam {n}", source=Source.STEAM)
                               for n in range(50)]), name="steam")
    gog = FakeSearch(Found([hit(f"g{n}", f"GOG {n}", source=Source.GOG)
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
