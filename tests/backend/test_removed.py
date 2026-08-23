"""Удалённое не возвращается: карточка уходит, а память о ней остаётся.

Ручная половина дедупликации. Что не склеила машина, показывается двумя
строками; человек убирает лишнюю, и она больше не приходит никогда — ни в
выдаче, ни кругом загрузки, ни одним лишним запросом.

Совпадение точное, по тройке «тип содержимого, источник, идентификатор»:
ложных срабатываний тут не бывает по построению, названия не сравниваются
вовсе."""

import sqlalchemy

from backend.model import Found, Kind, Source
from backend.service.hits import mark_of
from backend.service.removal import discard_card, remove_card
from backend.service.search import SEARCH_SIZE
from backend.storage.repository.library import LibraryRepository
from backend.storage.repository.removed import RemovedRepository
from tests.conftest import (
    FakeSearch,
    a_game,
    an_item,
    hit,
    poster_service,
    unreachable,
)
from tests.wiring import search_service

FALLOUT = (Kind.GAME, Source.STEAM, "38410")


async def rows(engine) -> list[tuple]:
    """Строки таблицы как есть: колонки читаются сырыми, чтобы наблюдать сам
    ключ, а не то, что о нём думает репозиторий."""
    async with engine.begin() as connection:
        found = await connection.execute(sqlalchemy.text(
            "SELECT kind, source, source_id, title FROM removed"))
        return [tuple(row) for row in found]


async def test_a_removed_row_is_remembered(removed, engine):
    """Запоминается тройка и название. Название — для человека: обратного хода
    в приложении нет, чинить придётся руками из SQLite, а по паре «steam /
    38410» не понять, что это было."""
    await removed.remember(a_game())

    assert await removed.known([FALLOUT]) == {FALLOUT}
    assert await rows(engine) == [("game", "steam", "38410", "Fallout 2")]


async def test_the_same_id_in_another_source_is_another_row(removed):
    """Ключ составной. Удалили строку Steam — гоговская остаётся: это разные
    записи о разных строках выдачи, и совпадение чисел ничего не значит."""
    await removed.remember(a_game())

    assert await removed.known([(Kind.GAME, Source.GOG, "38410")]) == set()


async def test_the_same_id_of_another_kind_is_another_row(removed, engine):
    """У TMDB фильмы и сериалы нумеруются порознь и сталкиваются числами:
    `tmdb/1399` — это и фильм, и «Игра престолов». Без типа содержимого в ключе
    удалённый фильм молча унёс бы сериал, а спека обещает, что ложных
    срабатываний не бывает по построению."""
    await removed.remember(an_item("1399", "Фильм", kind=Kind.MOVIE))

    assert await removed.known([(Kind.MOVIE, Source.TMDB, "1399")]) == {
        (Kind.MOVIE, Source.TMDB, "1399")
    }
    assert await removed.known([(Kind.SERIES, Source.TMDB, "1399")]) == set()

    # И обе строки уживаются: ключ их различает, а не отбрасывает вторую.
    await removed.remember(an_item("1399", "Сериал", kind=Kind.SERIES))
    assert len(await rows(engine)) == 2


async def test_removing_the_same_row_twice_is_quiet(removed, engine):
    """Убрать одну и ту же игру дважды человек вправе: завёл заново, посмотрел
    и убрал опять. Второй раз не должен ронять запись."""
    await removed.remember(a_game())
    await removed.remember(a_game(title="Fallout 2 переизданный"))

    assert len(await rows(engine)) == 1


async def test_nothing_asked_is_nothing_known(removed):
    """Пустой список не повод падать. Про «не повод идти в базу» тут не
    утверждается: пропущенный запрос не наблюдается — пустая таблица дала бы ту
    же пустоту."""
    assert await removed.known([]) == set()


async def test_a_manual_card_is_not_remembered(removed, engine):
    """У ручной карточки выдуманный `source_id`, и в выдаче она не появляется
    никогда — помнить о ней нечего. Записанная, она заняла бы строку, которая
    не отсеет ничего и никогда."""
    await removed.remember(an_item("сочинённый", "Своя игра",
                                   source=Source.MANUAL))

    assert await rows(engine) == []


async def test_discarding_a_card_removes_it_and_remembers_it(sessions, posters,
                                                             card):
    """Кнопка «удалить» обязана и убрать карточку, и закрыть ей дорогу обратно.
    Оба следствия проверяются разом: с одним первым политика слайса не
    наблюдалась бы вовсе."""
    item_id = await card(Kind.GAME, "38410")
    library = LibraryRepository(sessions)
    # Тройка берётся у самой карточки, а не пишется литералом: фикстура заводит
    # её со своим источником, и разъехавшийся литерал сделал бы проверку
    # зелёной при любой поломке.
    mark = mark_of(await library.get(item_id))

    await discard_card(library, poster_service(posters, unreachable()),
                       RemovedRepository(sessions), item_id)

    assert await library.get(item_id) is None
    assert await RemovedRepository(sessions).known([mark]) == {mark}


async def test_a_rollback_does_not_close_the_road_back(sessions, posters, card):
    """Тот же порядок удаления зовёт откат сорвавшейся записи, и там пометки
    быть не должно: карточка не сохранилась, а не была убрана человеком.
    Помеченная, она перестала бы находиться навсегда."""
    item_id = await card(Kind.GAME, "38410")
    library = LibraryRepository(sessions)
    mark = mark_of(await library.get(item_id))

    await remove_card(library, poster_service(posters, unreachable()), item_id)

    assert await library.get(item_id) is None
    assert await RemovedRepository(sessions).known([mark]) == set()


async def test_a_removed_candidate_never_reaches_the_search(sessions, reference,
                                                            removed):
    """Отсев стоит до показа: удалённая строка не мелькает и не исчезает — её
    нет с самого начала."""
    await removed.remember(a_game())
    found = FakeSearch(Found([
        hit("38410", "Fallout 2", source=Source.STEAM, kind=Kind.GAME),
        hit("38411", "Fallout Tactics", source=Source.STEAM, kind=Kind.GAME),
    ]), name="steam")

    result = await search_service(sessions, found).external(Kind.GAME, "fallout")

    assert [one.title for one in result.views] == ["Fallout Tactics"]


async def test_a_removed_row_of_one_source_leaves_the_other_alone(
    sessions, reference, removed
):
    """Удалили из Steam — гоговская строка на месте. Ровно ради этого ключ и
    составной: одна игра в двух магазинах — две разные строки выдачи."""
    await removed.remember(a_game())
    steam = FakeSearch(Found([
        hit("38410", "Fallout 2", source=Source.STEAM, kind=Kind.GAME),
    ]), name="steam")
    gog = FakeSearch(Found([
        hit("38410", "Fallout 2", source=Source.GOG, kind=Kind.GAME),
    ]), name="gog")

    result = await search_service(sessions, steam, gog).external(Kind.GAME,
                                                                "fallout")

    assert [one.source for one in result.views] == [Source.GOG]


async def test_the_removal_reaches_every_answer_and_not_only_the_first(
    sessions, reference, removed
):
    """У игр выдач две-три, а отсев берёт их списком. Урежься он до первой —
    убранная строка второго магазина возвращалась бы навсегда, при зелёном
    наборе: во всех прежних проверках убранное лежало в выдаче Steam, а она
    первая.

    Игры взяты разные нарочно. С одинаковыми названиями дефект прячет склейка:
    строка, которую отсев пропустил, слипается со своей парой и исчезает как
    проигравшая — то есть на экране всё верно по случайной причине."""
    await removed.remember(
        a_game("1207658691", "Fallout Tactics", source=Source.GOG))
    steam = FakeSearch(Found([
        hit("38410", "Fallout 2", source=Source.STEAM, kind=Kind.GAME),
    ]), name="steam")
    gog = FakeSearch(Found([
        hit("1207658691", "Fallout Tactics", source=Source.GOG, kind=Kind.GAME),
    ]), name="gog")

    result = await search_service(sessions, steam, gog).external(Kind.GAME,
                                                                "fallout")

    assert [one.title for one in result.views] == ["Fallout 2"]


async def test_a_huge_batch_of_marks_is_still_answered(removed, engine):
    """Набор спрашивается пачкой, и пачка бывает большой: клик по имени в музыке
    приводит до двадцати пяти исполнителей, у каждого до тысячи альбомов, и все
    они приходят сюда одним списком.

    У SQLite предел на число подставляемых значений, а тройка кладёт по три на
    строку — за ним запрос падает целиком, и поиск отвечает непредвиденным
    сбоем. Проверяется тем, что убранное всё равно находится: без разбиения на
    части этот вызов не доживает до ответа."""
    await removed.remember(a_game("38410"))
    many = [(Kind.GAME, Source.STEAM, str(n)) for n in range(20000)]

    found = await removed.known([*many, FALLOUT])

    assert found == {FALLOUT}


async def test_a_short_portion_after_cleaning_is_not_the_end(
        sessions, reference, removed):
    """Главное свойство догрузки. Из двадцати строк отсев убранного оставляет
    меньше, и «пришло мало» не значит «кончилось»: конец называет источник, а не
    длина списка после чистки. Считай мост по ней — и лента вставала бы на
    первой же убранной строке."""
    await removed.remember(an_item("0", "Дюна 0"))
    full = FakeSearch(Found([hit(str(n), f"Дюна {n}")
                             for n in range(SEARCH_SIZE)]))

    result = await search_service(sessions, full).external(Kind.MOVIE, "дюна")

    assert len(result.views) < SEARCH_SIZE
    assert result.more is True


async def test_a_removed_row_does_not_eat_a_slot(sessions, reference, removed):
    """Отсев стоит **до** среза порции. Иначе убранная строка занимала бы слот
    из двадцати, до экрана доезжало бы девятнадцать, а добрать двадцатую
    неоткуда: следующая порция начинается со следующего двадцатка."""
    await removed.remember(a_game("0"))
    many = FakeSearch(Found([
        hit(str(n), f"Игра {n}", source=Source.STEAM, kind=Kind.GAME)
        for n in range(SEARCH_SIZE + 5)
    ]), name="steam")

    result = await search_service(sessions, many).external(Kind.GAME, "игра")

    assert len(result.views) == SEARCH_SIZE
    assert "0" not in [one.source_id for one in result.views]


async def test_the_list_of_removed_is_narrowed_by_the_tab(removed):
    """Вкладка — первичный фильтр везде, и здесь тоже: во вкладке фильмов
    показывается только убранное кино.

    Свидетель с обоими типами нарочно: со списком из одних игр «сузили
    вкладкой» неотличимо от «отдали всё, что есть»."""
    await removed.remember(a_game("38410", "Fallout 2"))
    await removed.remember(
        an_item("550", "бойцовский клуб", kind=Kind.MOVIE, source=Source.TMDB))

    games = await removed.listing(Kind.GAME)
    films = await removed.listing(Kind.MOVIE)

    assert [(one.source_id, one.title) for one in games] == [
        ("38410", "Fallout 2")]
    # Название человек в этом списке видит, и пишется оно по общему правилу.
    # Свидетелем — фильм: он и заведён со строчной, а у Deezer строчные имена
    # обычное дело — такая строка показалась бы здесь не как везде.
    assert [one.title for one in films] == ["Бойцовский клуб"]


async def test_the_list_of_removed_knows_the_source_of_each_row(removed):
    """Источник нужен самой кнопке `restore`: снимают пометку по той же тройке,
    какой её ставили. Без него строку не с чем сопоставить."""
    await removed.remember(
        a_game("1207658691", "Fallout Tactics", source=Source.GOG))

    one, = await removed.listing(Kind.GAME)

    assert (one.kind, one.source, one.source_id) == (
        Kind.GAME, Source.GOG, "1207658691")


async def test_forgetting_lets_the_game_be_found_again(removed):
    """`restore` снимает только память об удалении. Карточка не возвращается —
    её нет вовсе, вместе с оценкой, тегами и обложкой; игра просто снова
    находится поиском.

    Наблюдается через `known`, а не через `listing`: пустой список сказал бы
    лишь, что строка исчезла из перечня, а важно, что отсев её больше не
    отбрасывает."""
    await removed.remember(a_game())
    assert await removed.known([FALLOUT]) == {("game", "steam", "38410")}

    await removed.forget(Kind.GAME, Source.STEAM, "38410")

    assert await removed.known([FALLOUT]) == set()


async def test_forgetting_touches_nobody_else(removed):
    """Снятие идёт по тройке целиком. Свидетель — сосед с тем же номером у
    другого источника: у Steam и GOG номера свои, и они сталкиваются."""
    await removed.remember(a_game("38410", "Fallout 2"))
    await removed.remember(a_game("38410", "Другая игра", source=Source.GOG))

    await removed.forget(Kind.GAME, Source.STEAM, "38410")

    assert [one.source for one in await removed.listing(Kind.GAME)] == [
        Source.GOG]


async def test_forgetting_what_was_not_removed_is_quiet(removed):
    """Человек нажимает `restore` дважды, страница успела дважды позвать мост —
    отказом это быть не должно: убирать нечего, и это исход, а не беда."""
    await removed.forget(Kind.GAME, Source.STEAM, "нет такого")

    assert await removed.listing(Kind.GAME) == []
