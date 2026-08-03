"""Что склеивается в одну строку выдачи, а что остаётся порознь.

Автоматическая половина дедупликации: то, что машина склеивает без единой
ошибки, она склеивает сама и человека не беспокоит. Замер боевой реализации —
383 верных склейки при нуле ложных, 83% из 461 верной пары на 224 запросах.

Что не склеилось — на глазах человека: он убирает лишнее руками, и это помнит
`RemovedRepository`.

Кто побеждает в группе и что забирает — `test_merging_winner.py`, сборники —
`test_merging_sets.py`."""

import pytest

from backend.model import Kind, SearchHit, Source
from backend.service.merging import merged
from tests.builders import row, titles


def test_two_editions_of_one_game_in_one_store_become_one():
    """Издания одной игры — одна игра, решение пользователя 02.08.2026.
    Побеждает строка без слов издания: показывать «Fallout 3» вернее, чем
    «Fallout 3 - Game of the Year Edition»."""
    steam = [row(Source.STEAM, "22300", "Fallout 3"),
             row(Source.STEAM, "22370", "Fallout 3 - Game of the Year Edition")]

    assert titles(merged([steam], "fallout 3")) == ["Fallout 3"]


def test_a_slug_glues_two_stores_whose_names_differ():
    """У Steam «The Witcher 3: Wild Hunt», у GOG «Ведьмак 3: Дикая Охота» —
    показываемые названия не совпадут никогда. Склеивает слаг, и ради этого он
    и доезжает до кандидата выдачи."""
    steam = [row(Source.STEAM, "292030", "The Witcher 3: Wild Hunt")]
    gog = [row(Source.GOG, "1207664663", "Ведьмак 3: Дикая Охота",
               aliases=("the witcher 3 wild hunt",))]

    assert titles(merged([steam, gog], "ведьмак 3")) == [
        "The Witcher 3: Wild Hunt"
    ]


def test_a_second_written_name_glues_a_localized_row():
    """Второе написание — самостоятельный ключ: показываемое название
    локализовано, а второе совпадает с тем, что показывает Steam.

    Кормит этот ключ old-games.ru — у него второе название лежит на странице.
    **GOG его не заполняет**: английское название знает только отдельный
    запрос, и брать его пользователь решил 03.08.2026 не стоящим того. Прежде
    тест назывался «английское название GOG», и по нему выходило, что ключ у
    GOG работает."""
    steam = [row(Source.STEAM, "1", "Baldur's Gate 3")]
    old = [row(Source.OLD_GAMES, "2", "Врата Балдура 3",
               original_title="Baldur's Gate 3")]

    assert titles(merged([steam, old], "baldurs gate")) == ["Baldur's Gate 3"]


def test_an_apostrophe_does_not_break_the_slug_key():
    """Слаг GOG апостроф съедает — `perimeter_emperors_testament`, — и
    приведение обязано съедать его так же. Раздели он слово пробелом, ключи
    разошлись бы у каждой игры с апострофом в названии.

    Замерено 03.08.2026 на независимой разметке: съеденный апостроф даёт 383
    верных склейки при нуле ложных против 380, и три прибавившиеся — «Периметр»
    и две «Heroes of Might and Magic III»."""
    steam = [row(Source.STEAM, "289240", "Perimeter: Emperor's Testament")]
    gog = [row(Source.GOG, "1454498998", "Периметр: Завет Императора",
               aliases=("perimeter emperors testament",))]

    assert titles(merged([steam, gog], "perimeter")) == [
        "Perimeter: Emperor's Testament"
    ]


def test_two_games_of_the_same_name_are_told_apart_by_the_year():
    """Однофамильцы: у old-games две карточки `Fallout` — 1997 года от Black
    Isle и 1991 года авторства Brad Taylor, и её страница прямо говорит «совсем
    не тот Fallout». Склеенные, они прятали настоящую игру и отдавали ей чужой
    год.

    Разошлись на шесть лет, и люфт в четыре их разводит. Решение пользователя
    03.08.2026."""
    steam = [row(Source.STEAM, "38400", "Fallout", year=1997)]
    old = [row(Source.OLD_GAMES, "30", "Fallout", year=1997),
           row(Source.OLD_GAMES, "5251", "Fallout", year=1991)]

    kept = [one for answer in merged([steam, old], "fallout") for one in answer]

    assert [(one.source_id, one.year) for one in kept] == [
        ("38400", 1997), ("5251", 1991)]


@pytest.mark.parametrize("later, kept", [(2001, ["1"]), (2002, ["1", "2"])])
def test_the_gap_is_four_years_and_the_fourth_still_counts(later, kept):
    """«Условно фаллаут 1997 и фаллаут 1999 — будет как одна игра, но не
    фаллаут 1991», словами пользователя. Люфт после перебора выбран им же —
    четыре.

    Границу сторожат обе половины сразу, и поодиночке они бессильны: свидетель
    на четыре разрешает и люфт побольше, свидетель на пять разрешает и поменьше.
    Вместе они запирают ровно четвёрку и заодно `>` против `>=`.

    Расходятся источники сплошь: у `Return to Castle Wolfenstein` 2001 против
    2002, у `Quake III Arena` 1999 против 2001 — регион, платформа,
    переиздание. Люфт для того и нужен."""
    steam = [row(Source.STEAM, "1", "Fallout", year=1997)]
    gog = [row(Source.GOG, "2", "Fallout", year=later)]

    shown = [one for answer in merged([steam, gog], "fallout") for one in answer]

    assert [one.source_id for one in shown] == kept


def test_a_row_without_a_year_never_objects():
    """Год известен не всем: у анонса его нет вовсе, у old-games бывает пусто.
    Пустота — не расхождение, и запрещать ею склейку значит развалить законные
    группы на ровном месте."""
    steam = [row(Source.STEAM, "1", "Fallout")]
    old = [row(Source.OLD_GAMES, "2", "Fallout", year=1997)]

    kept = [one for answer in merged([steam, old], "fallout") for one in answer]

    assert [one.source_id for one in kept] == ["1"]


def test_the_year_gap_holds_through_a_third_row():
    """Запрет смотрит все пары двух групп, а не только те две строки, которые
    сводят прямо сейчас.

    Свидетель: между `Fallout` 1997 и `Fallout` 1991 встаёт строка без года.
    Она законно склеивается с обеими по отдельности, и запрет, сравнивающий
    только сводимую пару, пропустил бы 1991-й в группу через неё.

    **Строка без года стоит первой нарочно.** Группы сводят за головы, а головой
    становится строка с наименьшим номером — то есть она. Своего года у неё нет,
    и запрет «по одной строке группы» промолчал бы: 1991-й въехал бы внутрь при
    зелёном наборе. Порядок выдач тут и есть то, что делает проверку способной
    упасть."""
    gog = [row(Source.GOG, "2", "Fallout")]
    steam = [row(Source.STEAM, "1", "Fallout", year=1997)]
    old = [row(Source.OLD_GAMES, "3", "Fallout", year=1991)]

    kept = [one for answer in merged([gog, steam, old], "fallout")
            for one in answer]

    assert [one.source_id for one in kept] == ["1", "3"]


def test_a_second_name_does_not_glue_inside_one_source():
    """Внутри одного источника ключ только один — показываемое название.
    Замерено: по второму названию склеиваются разные игры одной серии, и
    `Worms` c `Worms 2` — тот самый случай. Между источниками этого не
    случается, поэтому там добавочные ключи разрешены."""
    old = [row(Source.OLD_GAMES, "1", "Worms", original_title="Worms"),
           row(Source.OLD_GAMES, "2", "Worms 2", original_title="Worms")]

    assert titles(merged([old], "worms")) == ["Worms", "Worms 2"]


def test_a_third_row_does_not_drag_a_sibling_in_through_a_shared_key():
    """Главная ловушка склейки: объединение транзитивно, а замеренное правило
    попарно.

    `Worms` из Steam склеивается с `Worms` из old-games по названию, а та —
    с `Worms 2` по общему второму названию. Без проверки состава все трое
    оказываются одной игрой, и `Worms 2` исчезает — ровно то, что правило 4
    запрещает. Прежний тест брал те же две строки old-games **без** магазинной,
    то есть единственный случай, где дефекта нет."""
    steam = [row(Source.STEAM, "1", "Worms")]
    old = [row(Source.OLD_GAMES, "2", "Worms", original_title="Worms"),
           row(Source.OLD_GAMES, "3", "Worms 2", original_title="Worms")]

    assert titles(merged([steam, old], "worms")) == ["Worms", "Worms 2"]


def test_a_row_joins_by_its_own_name_before_its_alias():
    """У строки бывает два ключа, и очередь между ними решает исход.

    `Worms 2` из old-games знает своё название и второе — `Worms`. Примкни она
    сперва по второму, и её место займёт `Worms` из Steam, а `Worms 2` из
    Steam останется одна: `_joinable` вторую склейку уже запретит, и в выдаче
    появится третья строка — дубль `Worms`.

    Своё показываемое название сильнее псевдонима, и порядок ключей задан, а не
    взят из множества: обход `set` идёт по хешам, а хеш строки солится на
    запуск процесса. Замерено 03.08.2026 — до этой правки девять солей из
    шестнадцати давали дубль, семь верную пару, и все тесты были зелёными при
    любой."""
    steam = [row(Source.STEAM, "70600", "Worms"),
             row(Source.STEAM, "70610", "Worms 2")]
    old = [row(Source.OLD_GAMES, "1", "Worms 2", original_title="Worms"),
           row(Source.OLD_GAMES, "2", "Worms", original_title="Worms")]

    assert titles(merged([steam, old], "worms")) == ["Worms", "Worms 2"]


def test_two_ready_groups_merge_into_one():
    """Группы бывают глубже двух строк, и цепочка возникает сама: у Steam
    «Fallout 3» и его издание, у GOG — тоже пара, и стоит паре сойтись с парой,
    как в объединении появляется звено второго уровня.

    Все прежние проверки строили группы не глубже одной склейки, поэтому поиск
    корня, идущий по цепочке до конца, не наблюдался ничем: с одним шагом
    вместо цикла тот же вход отвечал бы `KeyError` — то есть исключением через
    границу потоков на обычном поиске."""
    steam = [row(Source.STEAM, "1", "Fallout 3"),
             row(Source.STEAM, "2", "Fallout 3 - Game of the Year Edition")]
    gog = [row(Source.GOG, "3", "Fallout 3"),
           row(Source.GOG, "4", "Fallout 3 Complete Edition")]

    assert titles(merged([steam, gog], "fallout 3")) == ["Fallout 3"]


def test_a_second_name_glues_between_sources():
    """Та же метка между источниками работает: у old-games русское название, а
    английское знает Steam."""
    steam = [row(Source.STEAM, "1", "Alone in the Dark")]
    old = [row(Source.OLD_GAMES, "2", "Один в темноте",
               original_title="Alone in the Dark")]

    assert titles(merged([steam, old], "alone")) == ["Alone in the Dark"]


def test_an_unknown_row_is_neither_glued_nor_lost():
    """Склейка не выбрасывает то, чего не узнала: строка, ни с чем не совпавшая,
    остаётся в выдаче как была."""
    steam = [row(Source.STEAM, "1", "Fallout 2")]
    gog = [row(Source.GOG, "2", "Arcanum")]

    assert titles(merged([steam, gog], "игра")) == ["Fallout 2", "Arcanum"]


def test_the_order_inside_a_source_survives():
    """Порядок задан источником и склейкой не перетасовывается: выдачу потом
    переплетают по кругу, и сдвинутый порядок сдвинул бы всю страницу."""
    steam = [row(Source.STEAM, str(n), f"Игра {n}") for n in range(5)]

    assert titles(merged([steam], "игра")) == [f"Игра {n}" for n in range(5)]


def test_two_films_of_the_same_name_are_not_glued():
    """Склейка работает только на играх. «Дюна» 1984 года и «Дюна» 2021-го —
    разные фильмы с одним названием, и по общему правилу они слились бы в одну
    строку.

    Прямым тестом, а не следствием чужого: до сих пор охранник падал только в
    `test_search.py`, где две строки приходят с `Kind.MOVIE` по недосмотру
    помощника, — то есть свойство модуля сторожила несогласованность чужой
    фикстуры."""
    tmdb = [SearchHit(kind=Kind.MOVIE, source=Source.TMDB, source_id="1",
                      title="Дюна", year=1984),
            SearchHit(kind=Kind.MOVIE, source=Source.TMDB, source_id="2",
                      title="Дюна", year=2021)]

    assert titles(merged([tmdb], "дюна")) == ["Дюна", "Дюна"]


def test_nothing_found_stays_nothing():
    assert merged([[], []], "что угодно") == [[], []]

