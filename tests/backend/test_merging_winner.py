"""Кто побеждает в группе склейки и что забирает у проигравших.

Победитель уходит целиком, и проигравшая строка исчезает вся — кроме имени на
другой письменности и года выхода. Оба исключения приняты решением пользователя
03.08.2026, и других нет.

Что вообще склеивается — `test_merging.py`."""

from backend.model import Source
from backend.service.merging import merged
from tests.builders import row, titles


def test_the_winner_picks_up_the_name_of_the_other_language():
    """Пара имён собирается здесь — до того, как проигравшие строки исчезнут.
    Группа склейки единственное место, где два имени **доказанно** про одну
    игру: их свело правило, а не догадка.

    Показываемое имя победителя не трогается: список выдачи от этого не меняется,
    а второе поле у кандидатов из магазинов и так пустое. Решение пользователя
    03.08.2026.

    Свидетель замеренный: Steam отдаёт `The Witcher 3: Wild Hunt`, GOG под своей
    локалью «Ведьмак 3: Дикая Охота», склеивает их слаг."""
    steam = [row(Source.STEAM, "292030", "The Witcher 3: Wild Hunt")]
    gog = [row(Source.GOG, "1207664663", "Ведьмак 3: Дикая Охота",
               aliases=("the witcher 3 wild hunt",))]

    kept = merged([steam, gog], "witcher 3")

    winner, = [one for answer in kept for one in answer]
    assert winner.title == "The Witcher 3: Wild Hunt"
    assert winner.original_title == "Ведьмак 3: Дикая Охота"


def test_a_winner_without_a_neighbour_keeps_its_own_second_name():
    """Пара собирается не всегда, и это исход, а не отказ: игра только в Steam —
    русского имени нет ниоткуда.

    Второй свидетель — old-games со своим вторым именем: чужого в группе нет, а
    своё обязано остаться. Без него «берём из группы» неотличимо от «затираем
    тем, что нашлось»."""
    alone = [row(Source.STEAM, "1", "Dishonored")]
    assert [one.original_title for answer in merged([alone], "dishonored")
            for one in answer] == [""]

    own = [row(Source.OLD_GAMES, "2", "Ил-2 Штурмовик",
               original_title="IL-2 Sturmovik")]
    assert [one.original_title for answer in merged([own], "ил-2")
            for one in answer] == ["IL-2 Sturmovik"]


def test_the_own_second_name_survives_when_it_is_of_the_same_script():
    """Своё второе имя не обязано быть на другой письменности, и затирать его
    пустотой не за что.

    Свидетели замерены живьём на запросе `dune`: `Dune II: The Building of a
    Dynasty` со вторым именем `Dune II: Battle for Arrakis`, `Emperor: Battle
    for Dune` с `Dune 3`. Обе строки одинокие — терять в группе нечего, — а поле
    после склейки становилось пустым."""
    own = [row(Source.OLD_GAMES, "1482", "Dune II: The Building of a Dynasty",
               original_title="Dune II: Battle for Arrakis")]

    winner, = [one for answer in merged([own], "dune") for one in answer]

    assert winner.original_title == "Dune II: Battle for Arrakis"


def test_the_second_name_is_taken_from_a_row_without_edition_words():
    """Второе имя выбирается тем же ключом, что и победитель: строка без слов
    издания вернее.

    Состав группы замерен живьём на запросе `gothic 2`: у old-games там обе
    строки — `Gothic II` с «Готика II» и `Gothic II: Gold Edition` с «Готика II .
    Gold», — и склеивает их снятие хвоста издания. Порядок внутри источника
    задаёт сам источник, поэтому свидетель ставит издание первым: этой
    перестановкой и решается, чьё имя достанется победителю."""
    steam = [row(Source.STEAM, "39510", "Gothic II: Gold Classic")]
    old = [row(Source.OLD_GAMES, "1", "Gothic II: Gold Edition",
               original_title="Готика II . Gold"),
           row(Source.OLD_GAMES, "2", "Gothic II", original_title="Готика II")]

    winner, = [one for answer in merged([steam, old], "gothic 2")
               for one in answer]

    assert winner.original_title == "Готика II"


def test_a_russian_name_with_latin_letters_is_not_the_english_one():
    """`S.T.A.L.K.E.R.: Тень Чернобыля` написан наполовину латиницей, и принять
    его за английское значит вытеснить настоящее английское из его поля.

    Свидетель нарочно с соседом: настоящее английское имя лежит в группе рядом,
    и без этой проверки оно проигрывало бы имени победителя."""
    steam = [row(Source.STEAM, "1", "S.T.A.L.K.E.R.: Тень Чернобыля")]
    old = [row(Source.OLD_GAMES, "2", "S.T.A.L.K.E.R.: Тень Чернобыля",
               original_title="S.T.A.L.K.E.R.: Shadow of Chernobyl")]

    winner, = [one for answer in merged([steam, old], "stalker")
               for one in answer]

    assert winner.title == "S.T.A.L.K.E.R.: Тень Чернобыля"
    assert winner.original_title == "S.T.A.L.K.E.R.: Shadow of Chernobyl"


def test_the_winner_takes_the_earliest_year_of_the_group():
    """Игра не могла выйти раньше самой себя — значит из разошедшихся дат верна
    ранняя. Решение пользователя 03.08.2026.

    Свидетель замеренный и не тавтологичный: у GOG «Heroes of Might and Magic 3:
    Complete» помечен 1999-м, у old-games «…Collector's Edition» — 2000-м.
    Разошлись они на год потому, что у второго издание позднее, и прав оказался
    ранний.

    Свидетель без года у победителя не случаен: Steam побеждает по приоритету,
    а года у него может не быть — у анонса его нет ни в одном поле. Без правила
    человек видел бы такую строку вообще без года, хотя соседи по группе его
    знают."""
    steam = [row(Source.STEAM, "1", "Heroes of Might and Magic 3")]
    gog = [row(Source.GOG, "2", "Heroes of Might and Magic 3", year=1999)]
    old = [row(Source.OLD_GAMES, "3", "Heroes of Might and Magic 3", year=2000)]

    winner, = [one for answer in merged([steam, gog, old], "heroes")
               for one in answer]

    assert winner.source is Source.STEAM
    assert winner.year == 1999


def test_a_later_year_of_the_winner_yields_to_an_earlier_one():
    """Правило действует и против самого победителя, а не только доливает ему
    пустое.

    Свидетель замеренный: `Wolfenstein 3D` у Steam помечен 1994 годом, а у GOG
    и old-games — 1992-м. Разошлись на два, то есть люфт их не разводит, и
    победителю достаётся ранний."""
    steam = [row(Source.STEAM, "2270", "Wolfenstein 3D", year=1994)]
    gog = [row(Source.GOG, "1441705226", "Wolfenstein 3D", year=1992)]

    winner, = [one for answer in merged([steam, gog], "wolfenstein 3d")
               for one in answer]

    assert winner.year == 1992


def test_a_group_without_years_leaves_the_year_alone():
    """Года может не быть ни у кого, и это исход, а не отказ: подставлять туда
    нечего."""
    steam = [row(Source.STEAM, "1", "Dune")]
    gog = [row(Source.GOG, "2", "Dune")]

    winner, = [one for answer in merged([steam, gog], "dune") for one in answer]

    assert winner.year is None


def test_the_winner_is_the_store_with_the_highest_priority():
    """Приоритет `steam > gog > old-games`, и поля не смешиваются: проигравшая
    строка уходит целиком, а не отдаёт победителю свои."""
    steam = [row(Source.STEAM, "1", "Dune")]
    gog = [row(Source.GOG, "2", "Dune")]
    old = [row(Source.OLD_GAMES, "3", "Dune")]

    kept = merged([old, gog, steam], "dune")

    assert titles(kept) == ["Dune"]
    survivor, = [one for answer in kept for one in answer]
    assert survivor.source is Source.STEAM


def test_the_ladder_of_priority_has_a_second_step_too():
    """Лестница проверяется и ниже первой ступени: с одним Steam перестановка
    GOG и old-games местами прошла бы молча, а порядок задан всеми тремя."""
    gog = [row(Source.GOG, "2", "Dune")]
    old = [row(Source.OLD_GAMES, "3", "Dune")]

    survivor, = [one for answer in merged([old, gog], "dune") for one in answer]

    assert survivor.source is Source.GOG
