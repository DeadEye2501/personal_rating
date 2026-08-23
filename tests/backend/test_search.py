"""Поиск по чужим базам: выдача, отказы и переплетение выдач — как двух
магазинов, так и двух половин одного источника.

Складывание своей выдачи с чужой — у `merge_results`, в своём модуле: оно живёт
в модели и зовётся ещё и с той стороны границы, мостом."""


import httpx

from backend.model import (
    ExternalId,
    Found,
    IdSource,
    Kind,
    Missing,
    PersonHit,
    RatingSource,
    Reason,
    Refusal,
    Source,
)
from backend.service.search import SEARCH_SIZE
from backend.sources.fantlab.client import FantLabClient
from backend.sources.http import SourceHttp
from tests.builders import recorded
from tests.conftest import MOMENT, FakeSearch, counting, hit, responding

# Записанный ответ FantLab, а не его копия по месту: рукописная разошлась бы с
# фикстурой молча — как уже разошлась, `edition_id` там был строкой.
PICNIC = recorded("fantlab/search_exact_isbn.json")





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
        ("андор", Kind.SERIES, 0),
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

    result = await service(client).external(Kind.MOVIE, "название")

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


async def test_the_portion_holds_works_of_every_namesake(sessions, service):
    """«По имени — работы всех людей с таким именем»: решение пользователя от
    02.08.2026, дословно.

    Сложенные подряд, работы первого тёзки съедают порцию целиком: у самого
    известного их обычно больше двадцати, и фильмографии остальных оказываются
    запрошены, оплачены и выброшены — замерено на «Джоне Траволте», двадцать
    строк, все его. Поэтому выдачи тёзок переплетаются между собой, как
    переплетаются два игровых магазина.

    Сверяется доля, а не членство: «взять по одной работе от каждого, а потом
    отдать остаток первому» на одной работе второго тёзки неотличимо от
    переплетения. Поэтому у второго их три, и порция обязана начаться с
    чередования.

    Длина фильмографии первого выведена из порции, а не написана числом: сравняй
    её с порцией — и складывание подряд позеленело бы молча."""
    client = FakeSearch(
        Found([]),
        people=Found([PersonHit("1"), PersonHit("2")]),
        works={"1": Found([hit(f"a{n}") for n in range(SEARCH_SIZE + 10)]),
               "2": Found([hit(f"b{n}") for n in range(3)])},
    )

    result = await service(client).external(Kind.MOVIE, "траволта")

    assert len(result.views) == SEARCH_SIZE
    assert [view.source_id for view in result.views][:6] == [
        "a0", "b0", "a1", "b1", "a2", "b2"
    ]


async def test_namesakes_who_worked_together_do_not_eat_the_portion_twice(
    sessions, service
):
    """Однофамильцы бывают соавторами: Коэны, Руссо, Вачовски. Фильмографии у
    них общие, и переплетение кладёт каждую работу дважды — по слоту от каждого
    брата, то есть половина порции уходит в близнецов.

    Снимать их надо здесь, до среза: складывание своей выдачи с чужой снимает
    близнеца уже после него, и до экрана доезжает вдвое меньше внешних строк,
    чем поместилось бы."""
    together = [hit(f"c{n}") for n in range(SEARCH_SIZE)]
    client = FakeSearch(Found([]),
                        people=Found([PersonHit("1"), PersonHit("2")]),
                        works={"1": Found(together), "2": Found(together)})

    result = await service(client).external(Kind.MOVIE, "руссо")

    shown = [view.source_id for view in result.views]
    assert shown == [one.source_id for one in together]


async def test_a_refusal_of_the_name_search_travels_as_a_refusal(sessions,
                                                                 service):
    """Отказ половины людей — поле в результате, а не исключение: у границы
    потоков второго канала доставки нет. Найденное по названию при этом
    доезжает."""
    client = FakeSearch(Found([hit()]),
                        people=Refusal(source="tmdb", reason=Reason.NETWORK))

    result = await service(client).external(Kind.MOVIE, "интерстеллар")

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

    result = await service(steam, gog).external(Kind.GAME, "игра")

    assert sorted(r.source for r in result.refusals) == ["gog", "steam"]


async def test_games_never_go_outside_for_people(sessions, service):
    """Кого спрашивать про людей — решает реестр, и сервис обязан его
    слушаться: у игр такого клиента нет вовсе."""
    client = FakeSearch(Found([]), people=Found([PersonHit("1")]), name="steam")

    await service(client).external(Kind.GAME, "игра")

    assert [one for one in client.asked if one[0] == "find_people"] == []


async def test_a_book_goes_outside_like_a_film(sessions, service):
    """Сторож, утверждавший обратное, стоял здесь с первого этапа: у книг не
    было источника, и внешняя половина выдачи была пуста по-настоящему.
    Источник появился, и половина обязана наполниться — иначе книга ищется
    только среди уже заведённых, а завести первую неоткуда."""
    client = FakeSearch(Found([hit(title="Дюна", kind=Kind.BOOK,
                                   source=Source.GOOGLE_BOOKS)]),
                        name="google_books", people=Found([]))

    result = await service(client).external(Kind.BOOK, "Дюна")

    assert [one.title for one in result.views] == ["Дюна"]
    assert ("Дюна", Kind.BOOK, 0) in client.asked


async def test_a_book_query_asks_for_the_author_too(sessions, service):
    """Следствие, приехавшее даром вместе с ответчиком за людей: строка ищет по
    имени всегда — решение пользователя 01.08.2026, — и набранное в ней приводит
    ещё и книги одноимённого автора. Ровно как у фильмов, и это условие задачи:
    поведение у книг не отличается ничем."""
    client = FakeSearch(Found([]), name="google_books",
                        people=Found([PersonHit("Фрэнк Герберт")]),
                        works=Found([hit(title="Дюна", kind=Kind.BOOK,
                                         source=Source.GOOGLE_BOOKS)]))

    result = await service(client).external(Kind.BOOK, "Фрэнк Герберт")

    assert [one.title for one in result.views] == ["Дюна"]
    assert ("find_people", "Фрэнк Герберт") in client.asked


async def test_an_album_goes_outside_like_a_film(sessions, service):
    """Последний тип, у которого внешней половины не было. Сторож, утверждавший
    обратное, стоял здесь с первого этапа: источника у музыки не было, и
    пустота была честной. Источник появился — половина обязана наполниться,
    иначе альбом ищется только среди уже заведённых, а завести первый
    неоткуда."""
    client = FakeSearch(Found([hit(title="Группа крови", kind=Kind.MUSIC,
                                   source=Source.DEEZER)]),
                        name="deezer", people=Found([]))

    result = await service(client).external(Kind.MUSIC, "группа крови")

    assert [one.title for one in result.views] == ["Группа крови"]
    assert ("группа крови", Kind.MUSIC, 0) in client.asked


async def test_the_offset_reaches_the_source(sessions, service):
    """Смещение — единственное, чем вторая порция отличается от первой. Не
    доедь оно до источника, лента догружала бы одно и то же двадцать строк
    подряд, а человек видел бы, что прокрутка не двигается."""
    client = FakeSearch(Found([hit()]))

    await service(client).external(Kind.MOVIE, "дюна", offset=SEARCH_SIZE)

    assert client.asked == [("дюна", Kind.MOVIE, SEARCH_SIZE)]


async def test_a_full_portion_means_there_is_more(sessions, service):
    """Конец выдачи называет источник, а не длина показанного. Полная порция —
    единственное, что о нём известно: `totalItems` у Google всегда `300` и
    врёт, замерено."""
    full = Found([hit(str(n), f"Дюна {n}") for n in range(SEARCH_SIZE)])

    answer = await service(FakeSearch(full)).external(Kind.MOVIE, "дюна")

    assert answer.more is True


async def test_singles_thrown_out_do_not_stop_the_feed(sessions, service):
    """Отсев укорачивает порцию, а «есть ещё» считается до него.

    Замерено 23.08.2026: по «дельфин» из двадцати строк Deezer семь помечены
    синглом. Считай признак по показанному — тринадцать строк объявили бы конец
    выдачи, и альбом со второй страницы был бы недостижим ничем: у музыки это
    почти каждый поиск.

    Свидетель — полная порция, где часть строк уходит отсевом; сам отсев
    проверяется рядом, по числу показанных."""
    rows = [hit(str(n), f"Дельфин {n}", kind=Kind.MUSIC, source=Source.DEEZER,
                single=n % 3 == 0)
            for n in range(SEARCH_SIZE)]

    answer = await service(FakeSearch(Found(rows))).external(Kind.MUSIC, "дельфин")

    assert answer.more is True, "отсев погасил догрузку"
    assert len(answer.views) == SEARCH_SIZE - len(range(0, SEARCH_SIZE, 3))


async def test_a_single_is_not_shown_in_the_search(sessions, service):
    """Приложение оценивает альбомы: сингл не показывается и потому не заводится
    в базу — решение пользователя 23.08.2026."""
    rows = [hit("1", "Группа крови", kind=Kind.MUSIC, source=Source.DEEZER),
            hit("2", "Дельфин", kind=Kind.MUSIC, source=Source.DEEZER,
                single=True)]

    answer = await service(FakeSearch(Found(rows))).external(Kind.MUSIC, "д")

    assert [one.title for one in answer.views] == ["Группа крови"]


async def test_the_end_of_the_source_stops_the_feed(sessions, service):
    """Обратная половина: источник отдал меньше запрошенного — признак гаснет,
    и лента перестаёт просить. Без неё бесконечный цикл в `Feed.more()`
    выглядит как зависшее окно."""
    answer = await service(FakeSearch(Found([hit()]))).external(Kind.MOVIE, "д")

    assert answer.more is False


async def test_a_source_that_cannot_page_is_not_asked_twice(sessions, service):
    """Спрашивать нелистающий источник второй раз — не ошибка выдачи, а
    потраченный запрос: у Google их тысяча в сутки. Наблюдается счётом
    запросов, а не выдачей: выдача одинакова в обоих случаях."""
    client = FakeSearch(Found([hit(source=Source.STEAM)]), name="steam",
                        pages=False)

    await service(client).external(Kind.GAME, "дюна", offset=SEARCH_SIZE)

    assert client.asked == []


async def test_a_full_portion_from_a_source_that_cannot_page_is_the_end(
        sessions, service):
    """Полная порция от того, кто листать не умеет, — всё равно конец: второй
    порции у него не бывает. Скажи мост «есть ещё» — и лента сходила бы за
    заведомо пустой выдачей на каждый поиск игры."""
    full = Found([hit(str(n), f"Игра {n}", source=Source.STEAM, kind=Kind.GAME)
                  for n in range(SEARCH_SIZE)])
    client = FakeSearch(full, name="steam", pages=False)

    answer = await service(client).external(Kind.GAME, "игра")

    assert answer.more is False


async def test_the_works_of_namesakes_are_asked_once_per_search(sessions,
                                                                service):
    """Вторая половина выдачи не листается вовсе, и перезапрашивать её на каждой
    порции значит слать те же запросы впустую: их результат всё равно снимет
    `merge_results`, а у книг из тысячи суточных уйдёт по два на порцию."""
    client = FakeSearch(Found([]), people=Found([PersonHit("1")]),
                        works=Found([hit()]))

    await service(client).external(Kind.MOVIE, "нолан", offset=SEARCH_SIZE)

    assert [one for one in client.asked if one[0] == "find_people"] == []


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
        result = await search.external(Kind.GAME, "игра")

    assert result.views == ()
    assert (result.refusals[0].source, result.refusals[0].reason) == (
        "steam", Reason.BROKEN
    )
    assert "разбор не удался" in result.refusals[0].detail
    assert [r for r in caplog.records if r.name.startswith("backend")] != []


async def test_a_broken_client_does_not_hide_the_other(sessions, service):
    """Второй магазин отвечает своё, и его находки доезжают."""
    broken = FakeSearch(RuntimeError("сорвался"), name="steam")
    gog = FakeSearch(Found([hit("1207664663", "Ведьмак", kind=Kind.GAME, source=Source.GOG)]),
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
    и типом, что пришли снаружи.

    Названия у строк разные нарочно: одноимённые склеились бы в одну — и верно
    склеились бы, — а тут считается, что спросили обоих."""
    steam = FakeSearch(
        Found([hit("292030", "Ведьмак 3", kind=Kind.GAME, source=Source.STEAM)]),
        name="steam")
    gog = FakeSearch(
        Found([hit("1207664663", "Ведьмак 2", kind=Kind.GAME, source=Source.GOG)]),
        name="gog")

    result = await service(steam, gog).external(Kind.GAME, "ведьмак")

    assert len(result.views) == 2
    assert steam.asked == [("ведьмак", Kind.GAME, 0)]
    assert gog.asked == [("ведьмак", Kind.GAME, 0)]


async def test_two_stores_come_woven_and_not_in_blocks(sessions, service):
    """Спека требует «показывают вперемешку». Подряд это значит, что вторая
    половина страницы — всегда GOG, а он на бессмыслицу отдаёт два десятка
    несвязанных игр: настоящие находки уехали бы за экран."""
    steam = FakeSearch(Found([hit(f"s{n}", f"Игра S{n}", kind=Kind.GAME, source=Source.STEAM)
                               for n in range(3)]), name="steam")
    gog = FakeSearch(Found([hit(f"g{n}", f"Игра G{n}", kind=Kind.GAME, source=Source.GOG)
                             for n in range(3)]), name="gog")

    result = await service(steam, gog).external(Kind.GAME, "игра")

    assert [v.source_id for v in result.views] == [
        "s0", "g0", "s1", "g1", "s2", "g2"
    ]


async def test_three_answers_are_woven_by_turns(sessions, service):
    """У игр источников три — Steam, GOG и old-games, — а собиралась выдача из
    трёх ни разу: во всех прежних проверках `_weave` получал одну или две.

    Порядок «по одному кандидату по кругу» на трёх выдачах разной длины и есть
    предмет: с двумя он неотличим от простого чередования, а третий источник
    приписан этим же планом."""
    steam = FakeSearch(Found([hit(f"s{n}", f"Игра S{n}", kind=Kind.GAME,
                                  source=Source.STEAM) for n in range(3)]),
                       name="steam")
    gog = FakeSearch(Found([hit("g0", "Игра G0", kind=Kind.GAME,
                                source=Source.GOG)]), name="gog")
    old = FakeSearch(Found([hit(f"o{n}", f"Игра O{n}", kind=Kind.GAME,
                                source=Source.OLD_GAMES) for n in range(2)]),
                     name="old_games")

    result = await service(steam, gog, old).external(Kind.GAME, "игра")

    assert [one.title for one in result.views] == [
        "Игра S0", "Игра G0", "Игра O0", "Игра S1", "Игра O1", "Игра S2",
    ]


async def test_a_shorter_answer_does_not_leave_a_hole(sessions, service):
    """Магазины отдают разное число находок — переплетение это переживает."""
    steam = FakeSearch(Found([hit(f"s{n}", f"Игра S{n}", kind=Kind.GAME, source=Source.STEAM)
                               for n in range(3)]), name="steam")
    gog = FakeSearch(Found([hit("g0", "Игра G0", kind=Kind.GAME, source=Source.GOG)]), name="gog")

    result = await service(steam, gog).external(Kind.GAME, "игра")

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
    gog = FakeSearch(Found([hit("1207664663", "Ведьмак", kind=Kind.GAME, source=Source.GOG)]),
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

    result = await service(steam, gog).external(Kind.GAME, "игра")

    assert result.views == ()
    assert sorted(r.source for r in result.refusals) == ["gog", "steam"]


async def test_one_game_from_two_stores_becomes_one_row(sessions, service):
    """Склейка стоит в сборке выдачи, а не только в своём модуле. Без вызова
    здесь человек по-прежнему видел бы две строки одной игры, а все проверки
    самой склейки оставались бы зелёными.

    Строки нарочно игровые: у кино источник один, склеивать там нечего, и на
    умолчании помощника — а оно `Kind.MOVIE` — эта проверка не наблюдала бы
    ничего."""
    steam = FakeSearch(Found([hit("1", "Fallout 2", source=Source.STEAM,
                                  kind=Kind.GAME)]), name="steam")
    gog = FakeSearch(Found([hit("2", "Fallout 2", source=Source.GOG,
                                kind=Kind.GAME)]), name="gog")

    result = await service(steam, gog).external(Kind.GAME, "fallout 2")

    assert [one.source for one in result.views] == [Source.STEAM]


async def test_the_portion_is_cut_before_the_merging(sessions, service):
    """Порядок этих двух шагов виден человеку. Склейка по полным выдачам даёт
    победителя с сороковой строки, который убивает проигравшего со второй, — и
    на экран не попадает ни один из двух.

    Здесь у Steam и GOG совпадает единственная пара названий, и стоит она за
    краем порции у одного из них: срезав порцию первой, склейка её не увидит и
    ничего не тронет."""
    steam = FakeSearch(Found(
        [hit(f"s{n}", f"Игра S{n}", source=Source.STEAM, kind=Kind.GAME)
         for n in range(SEARCH_SIZE)]
        + [hit("s-late", "Общая игра", source=Source.STEAM, kind=Kind.GAME)]
    ), name="steam")
    gog = FakeSearch(Found(
        [hit("g0", "Общая игра", source=Source.GOG, kind=Kind.GAME)]
    ), name="gog")

    result = await service(steam, gog).external(Kind.GAME, "игра")

    assert "Общая игра" in [one.title for one in result.views]
    assert len(result.views) == SEARCH_SIZE + 1


async def test_a_portion_is_counted_per_source_and_not_per_page(sessions, service):
    """У игр магазина два, и по 20 у каждого — это два запроса, как и сказано в
    спеке. Срез на общей выдаче отдал бы 20 на двоих."""
    steam = FakeSearch(Found([hit(f"s{n}", f"Игра S{n}", kind=Kind.GAME, source=Source.STEAM)
                               for n in range(50)]), name="steam")
    gog = FakeSearch(Found([hit(f"g{n}", f"Игра G{n}", kind=Kind.GAME, source=Source.GOG)
                             for n in range(50)]), name="gog")

    result = await service(steam, gog).external(Kind.GAME, "игра")

    assert len(result.views) == 2 * SEARCH_SIZE


def _fantlab(payload: dict, picture: str = "image/jpeg") -> FantLabClient:
    """Настоящий клиент запасного источника на подставном транспорте.

    Настоящий, а не двойник, и это главное в проверке ниже: `_covered` зовёт у
    него не только `cover_for`, но и `name` — подписывать им ответ. Двойник
    отвечает на что угодно, и потерянное свойство прошло бы молча; живьём это
    ровно так и случилось 23.08.2026, при зелёном наборе.

    Транспорт различает две ручки: поиск издания и `HEAD` за картинкой."""
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.fantlab.ru":
            return httpx.Response(200, json=payload)
        return httpx.Response(200, headers={"content-type": picture})

    return FantLabClient(SourceHttp("fantlab", transport=httpx.MockTransport(handler)))


async def test_a_book_without_a_cover_gets_one_from_the_spare_source(
    sessions, service
):
    """Обложка добывается на стороне и доезжает до строки выдачи.

    Ради этого источник и заведён: у Google обложки местами нет вовсе, а
    человек выбирает из выдачи глазами. Спрашивается это при поиске, а не при
    заведении карточки, — решение пользователя 23.08.2026."""
    naked = hit("VOL1", "Пикник на обочине", kind=Kind.BOOK,
                source=Source.GOOGLE_BOOKS,
                external_ids=(ExternalId(IdSource.ISBN, "9785170829835"),))
    search = service(FakeSearch(Found([naked])), covers=_fantlab(PICNIC))

    result = await search.external(Kind.BOOK, "пикник на обочине")

    assert result.views[0].poster_url == (
        "https://fantlab.ru/images/editions/orig/118084"
    )


async def test_a_book_the_spare_source_does_not_know_stays_bare(sessions, service):
    """Отказ запасного источника ничего не ломает: строка показывается без
    обложки, как показывалась бы и без него вовсе."""
    naked = hit("VOL1", "Пикник на обочине", kind=Kind.BOOK,
                source=Source.GOOGLE_BOOKS,
                external_ids=(ExternalId(IdSource.ISBN, "9785170829835"),))
    search = service(FakeSearch(Found([naked])),
                     covers=_fantlab({"matches": [], "total_found": 0}))

    result = await search.external(Kind.BOOK, "пикник на обочине")

    assert result.views[0].poster_url == ""
    assert result.refusals == ()


async def test_a_book_that_already_has_a_cover_asks_nobody(sessions, service):
    """Обложка добывается на стороне только тем, у кого её нет: у Google
    картинка есть у большинства английских изданий, и спрашивать про них чужой
    каталог значит слать порцию лишних запросов на каждый поиск — а показать
    всё равно нечего нового.

    Свидетелем — счётчик запросов: адрес строки при лишнем походе остался бы
    прежним, потому что своя обложка сильнее, и подмена прошла бы молча."""
    dressed = hit("VOL1", "Пикник на обочине", kind=Kind.BOOK,
                  source=Source.GOOGLE_BOOKS,
                  poster_url="https://books.google.com/c?id=1",
                  external_ids=(ExternalId(IdSource.ISBN, "9785170829835"),))
    transport, seen = counting(responding(json=PICNIC))
    search = service(FakeSearch(Found([dressed])),
                     covers=FantLabClient(
                         SourceHttp("fantlab", transport=transport)))

    result = await search.external(Kind.BOOK, "пикник на обочине")

    assert result.views[0].poster_url == "https://books.google.com/c?id=1"
    assert seen == [], "обложку искали тому, у кого она есть"


async def test_a_film_asks_no_spare_source(sessions, service):
    """Запасной источник есть только у книг: у остальных обложку отдаёт сам
    каталог, и лишний запрос стоил бы порции лишних походов в сеть.

    Свидетелем — клиент, который на любой вопрос отвечает картинкой: спроси его
    сервис, и у фильма появился бы адрес FantLab."""
    naked = hit("157336", "Интерстеллар")
    search = service(FakeSearch(Found([naked])), covers=_fantlab(PICNIC))

    result = await search.external(Kind.MOVIE, "интерстеллар")

    assert result.views[0].poster_url == ""
