"""Строка выдачи обязана знать, о чём её спросили.

У GOG нет понятия «не найдено»: на бессмыслицу он отдаёт два десятка несвязанных
игр. Замерено 03.08.2026 боевым кодом — на русском запросе 94% показанного
мусор, на английском 23%.

Решение пользователя того же дня: «или адекватная выдача, или не быть вообще».
"""

import pytest

from backend.model import Found, Kind, PersonHit, SearchHit, Source
from backend.service.relevance import relevant
from backend.service.search import SEARCH_SIZE
from tests.builders import titles
from tests.conftest import FakeSearch, hit
from tests.wiring import search_service


def row(title: str, *, original_title: str = "",
        aliases: tuple[str, ...] = ()) -> SearchHit:
    return SearchHit(kind=Kind.GAME, source=Source.GOG, source_id="1",
                     title=title, original_title=original_title,
                     aliases=aliases)


def test_a_row_that_knows_no_word_of_the_query_is_not_shown():
    """Ровно то, что видит человек сегодня: по «ведьмак 3» GOG отдаёт двадцать
    строк, и первые — `Baldur's Gate 3` и `Broken Sword 3`."""
    answers = [[row("The Witcher 3: Wild Hunt"), row("Baldur's Gate 3")]]

    assert titles(relevant(answers, "witcher 3")) == ["The Witcher 3: Wild Hunt"]


def test_the_words_may_come_from_different_fields_of_the_row():
    """Слова строки складываются в одну кучу: одно слово запроса может найтись в
    названии, другое — в слаге.

    Это главное свойство правила «все слова», и без него запрос «ведьмак 3» не
    нашёл бы гоговскую строку: показываемое название у неё русское, тройка в
    нём есть, а слово `witcher` — только в слаге. Попольная проверка «в каком-то
    одном поле все слова» выбросила бы её."""
    split = row("Ведьмак 3: Дикая Охота",
                aliases=("the witcher 3 wild hunt",))

    assert titles(relevant([[split]], "witcher 3")) == ["Ведьмак 3: Дикая Охота"]
    assert titles(relevant([[split]], "ведьмак hunt")) == [
        "Ведьмак 3: Дикая Охота"
    ]


def test_every_word_of_the_query_has_to_be_there():
    """Строка обязана знать **все** слова запроса, а не хоть одно.

    С «хоть одним» по «x com» пролезало 14 строк из 68, а `s.t.a.l.k.e.r`
    приведение режет на семь однобуквенных слов — и любая строка с буквой `s`
    в названии проходила. Замерено на живых источниках 03.08.2026."""
    rows = [row("X-COM: UFO Defense"), row("Combat Mission"), row("X Rebirth")]

    assert titles(relevant([rows], "x com")) == ["X-COM: UFO Defense"]


def test_a_possessive_name_is_found_by_its_bare_word():
    """Апостроф при приведении исчезает, и `Baldur's` становится одним словом
    `baldurs` — на букву длиннее того, что набирает человек. Без этого правила
    запрос «baldur» не находил **ничего**: замерено на живых источниках, 19
    строк на входе и ноль на экране.

    Правило узкое нарочно — только форма на `s`. Совпадение началом слова
    замерено и отвергнуто: по «x com» оно пропускает 62 строки из 68 вместо 14,
    а `s.t.a.l.k.e.r` приведение режет на однобуквенные слова, и началом слова
    проходит что угодно."""
    answers = [[row("Baldur's Gate 3"), row("Assassin's Creed"),
                row("Combat Mission")]]

    assert titles(relevant(answers, "baldur")) == ["Baldur's Gate 3"]
    assert titles(relevant(answers, "assassin")) == ["Assassin's Creed"]
    assert titles(relevant(answers, "com")) == []


def test_a_number_narrows_the_text_it_stands_with():
    """Цифра — слово наравне с текстом, и она **сужает**. Решение пользователя
    03.08.2026: «Герои» находят все части, «Герои 3» — только третью.

    Без неё `Heroes of Might and Magic: Olden Era` выходит первой строкой на
    запрос про третьих «Героев»: все текстовые слова у неё есть, а это другая
    игра, замерено на живом Steam."""
    rows = [row("Heroes of Might and Magic III"),
            row("Heroes of Might and Magic: Olden Era"),
            row("Heroes of Might and Magic IV")]

    assert titles(relevant([rows], "heroes of might and magic 3")) == [
        "Heroes of Might and Magic III"
    ]
    assert len(relevant([rows], "heroes of might and magic")[0]) == 3


def test_a_second_name_and_an_alias_count_as_the_row_knowing_the_word():
    """Слова строки берутся оттуда же, откуда ключи склейки. Без псевдонима
    `Кровная вражда: Ведьмак. Истории` выпала бы на запросе «witcher» — а это
    настоящая игра серии, показанная GOG под русским названием. Спасает её слаг,
    и это замерено, а не предположено."""
    answers = [[
        row("Кровная вражда: Ведьмак. Истории",
            aliases=("thronebreaker the witcher tales",)),
        row("Один в темноте", original_title="Alone in the Dark"),
        row("Baldur's Gate 3"),
    ]]

    assert titles(relevant(answers, "witcher")) == [
        "Кровная вражда: Ведьмак. Истории"
    ]
    assert titles(relevant(answers, "alone")) == ["Один в темноте"]


def test_films_and_series_are_not_filtered():
    """Правило замерено на играх и держится их свойством: у GOG нет понятия «не
    найдено», поэтому на бессмыслицу он отвечает чем попало. У TMDB оно есть.

    Больше того, кино правило **портит**: TMDB ищет по переводам и альтернативным
    названиям, которых в строке нет вовсе, а показываемое название приезжает
    по-русски. Замерено 03.08.2026 на живом API — по «the lives of others» из
    четырёх строк уцелела бы одна, и не та: у немецкого фильма нет слов запроса
    ни в русском названии, ни в оригинале `Das Leben der Anderen`. У
    «Унесённых призраками» оригинал `千と千尋の神隠し`, и приведение даёт пустую
    строку — знать запрос ей нечем в принципе.

    Тем же способом и по тому же доводу из склейки исключено кино."""
    films = [[SearchHit(kind=Kind.MOVIE, source=Source.TMDB, source_id="129",
                        title="Унесённые призраками",
                        original_title="千と千尋の神隠し")]]

    assert titles(relevant(films, "spirited away")) == ["Унесённые призраками"]


def test_an_empty_query_filters_nothing():
    """Пустой набор слов выбросил бы всю выдачу целиком: `all()` на пустом
    истинно, и без этой ветки правило работало бы наоборот.

    Одни цифры пустотой не считаются — цифра слово, и «2024» сужает, как всякое
    другое."""
    answers = [[row("Fallout 2"), row("FlatOut 2")]]

    assert titles(relevant(answers, "  ")) == ["Fallout 2", "FlatOut 2"]
    assert titles(relevant(answers, "")) == ["Fallout 2", "FlatOut 2"]
    assert titles(relevant(answers, "2")) == ["Fallout 2", "FlatOut 2"]
    assert titles(relevant(answers, "2024")) == []


def test_the_order_and_the_shape_of_the_answers_survive():
    """Отсев убирает строки и не трогает ничего больше.

    В первой выдаче уцелевших нарочно **две**: с одной перевёрнутый порядок
    внутри выдачи был бы неотличим от сохранённого, а порядок этот задал
    источник — у него есть данные о популярности, которых у нас нет.

    Выдачи разложены по своим спискам, а не слиты в один: по ним идёт
    переплетение."""
    answers = [[row("Dune"), row("Dude, Where Is My Beer?"), row("Dune 2000")],
               [row("Dune: Spice Wars")],
               [row("Rune Classic")]]

    kept = relevant(answers, "dune")

    assert [len(one) for one in kept] == [2, 1, 0]
    assert [[one.title for one in answer] for answer in kept] == [
        ["Dune", "Dune 2000"], ["Dune: Spice Wars"], [],
    ]


async def test_the_works_of_a_namesake_are_not_filtered(sessions, reference):
    """**Место, где эта правка могла бы тихо всё сломать.**

    Строка поиска ищет и по имени человека — решение пользователя 01.08.2026, —
    и работы тёзок приезжают той же выдачей. Но запрос там имя, а строки — его
    фильмы, и общего слова у «Джона Траволты» с «Криминальным чтивом» нет ни
    одного. Общий отсев отменил бы поиск по имени целиком."""
    client = FakeSearch(Found([]), people=Found([PersonHit("8891")]),
                        works=Found([hit("680", "Криминальное чтиво")]))

    result = await search_service(sessions, client).external(
        Kind.MOVIE, "джон траволта")

    assert [one.title for one in result.views] == ["Криминальное чтиво"]


async def test_the_junk_does_not_eat_a_slot(sessions, reference):
    """Отсев стоит **до** среза порции. Иначе двадцать мусорных строк заняли бы
    двадцать слотов, и до экрана не доехало бы ничего — ровно то, что сегодня
    происходит по запросу «ведьмак 3».

    Мусора нарочно больше порции: с меньшим числом «отсеяли до среза» и
    «отсеяли после» неразличимы."""
    rows = [hit(f"j{n}", f"Чужая игра {n}", kind=Kind.GAME, source=Source.GOG)
            for n in range(SEARCH_SIZE)]
    rows.append(hit("real", "Fallout 2", kind=Kind.GAME, source=Source.GOG))
    client = FakeSearch(Found(rows), name="gog")

    result = await search_service(sessions, client).external(Kind.GAME,
                                                            "fallout")

    assert [one.title for one in result.views] == ["Fallout 2"]


@pytest.mark.parametrize(("query", "title", "shown"), [
    ("ил-2 штурмовик", "Ил-2 Штурмовик", True),
    ("ил-2 штурмовик", "Ил-2 Штурмовик: Забытые сражения", True),
    ("ил-2 штурмовик", "Тачки 2", False),
    ("витчер", "The Witcher 3: Wild Hunt", False),
])
def test_the_measured_cases_behave_as_measured(query, title, shown):
    """Свидетели из замера 03.08.2026, включая тот, ради которого правило и
    принято: «ил-2 штурмовик» сегодня даёт двадцать строк, из которых
    девятнадцать посторонних.

    Последняя строка — про русский запрос английской игры: он честно не даёт
    ничего, и это лучше, чем `Baldur's Gate 3` первой строкой."""
    assert bool(titles(relevant([[row(title)]], query))) is shown
