"""Одна игра — одна строка выдачи.

Автоматическая половина дедупликации: то, что машина склеивает без единой
ошибки, она склеивает сама и человека не беспокоит. Замер принятого правила —
382 верных склейки при нуле ложных, 83% из 461 верной пары на 224 запросах.

Что не склеилось — на глазах человека: он убирает лишнее руками, и это задача 4."""

from backend.model import Kind, SearchHit, Source
from backend.service.merging import merged


def row(source: Source, source_id: str, title: str, *,
        original_title: str = "", aliases: tuple[str, ...] = ()) -> SearchHit:
    return SearchHit(
        kind=Kind.GAME, source=source, source_id=source_id, title=title,
        original_title=original_title, aliases=aliases,
    )


def titles(answers: list[list[SearchHit]]) -> list[str]:
    return [one.title for answer in answers for one in answer]


def test_two_editions_of_one_game_in_one_store_become_one():
    """Издания одной игры — одна игра, решение пользователя 02.08.2026.
    Побеждает строка без слов издания: показывать «Fallout 3» вернее, чем
    «Fallout 3 - Game of the Year Edition»."""
    steam = [row(Source.STEAM, "22370", "Fallout 3"),
             row(Source.STEAM, "22300", "Fallout 3 - Game of the Year Edition")]

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


def test_the_english_name_of_gog_glues_too():
    """Второй ключ GOG — английское название: локализованное у него своё, а
    английское совпадает с тем, что показывает Steam."""
    steam = [row(Source.STEAM, "1", "Baldur's Gate 3")]
    gog = [row(Source.GOG, "2", "Врата Балдура 3",
               original_title="Baldur's Gate 3")]

    assert titles(merged([steam, gog], "baldurs gate")) == ["Baldur's Gate 3"]


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


def test_a_compilation_does_not_show_up_at_all():
    """Сборник — не издание: это несколько игр под одной строкой. Решение
    пользователя 03.08.2026 — убирать вовсе.

    Сборник взят такой, что ни с чем в выдаче не склеивается: с «Mafia Trilogy»
    рядом с «Mafia» проверка была бы зелёной и при снятом отсеве — слово
    `trilogy` есть и среди издательских, и строка ушла бы как издание.
    Заплачено за это решение пятнадцатью настоящими строками, и сторожить его
    надо тем, что без него не сходится."""
    steam = [row(Source.STEAM, "1", "Mafia"),
             row(Source.STEAM, "2", "Deus Ex Bundle")]

    assert titles(merged([steam], "mafia")) == ["Mafia"]


def test_the_asked_compilation_stays_and_the_others_do_not():
    """Исключение из того же решения, уточнённое пользователем 03.08.2026:
    остаётся **тот** сборник, который спросили, а не все сборники подряд.

    Обе стороны в одном тесте нарочно: с одной строкой в выдаче исключение
    неотличимо от «отсев выключился целиком», а посторонние сборники в выдаче
    того же запроса — обычное дело."""
    steam = [row(Source.STEAM, "1", "Mortal Kombat Trilogy"),
             row(Source.STEAM, "2", "SUPERHOT ONE OF US BUNDLE")]

    assert titles(merged([steam], "mortal kombat trilogy")) == [
        "Mortal Kombat Trilogy"
    ]


def test_the_asked_compilation_is_matched_by_words_and_not_by_letters():
    """Сравниваются приведённые слова, а не строка целиком: человек набирает
    как придётся — со строчной буквы, без знаков, «and» вместо «&»."""
    steam = [row(Source.STEAM, "1", "Command & Conquer: The Ultimate Collection")]

    assert titles(merged([steam], "command and conquer ultimate collection")) == [
        "Command & Conquer: The Ultimate Collection"
    ]


def test_a_compilation_stays_hidden_when_the_query_did_not_name_one():
    """Обе половины правила нужны разом. По «fallout» слова запроса в названии
    «Fallout Classic Collection» есть, а сборника человек не просил — и строка
    остаётся скрытой. Ровно эти строки спека и назвала ценой решения."""
    steam = [row(Source.STEAM, "1", "Fallout"),
             row(Source.STEAM, "2", "Fallout Classic Collection")]

    assert titles(merged([steam], "fallout")) == ["Fallout"]


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


def test_nothing_found_stays_nothing():
    assert merged([[], []], "что угодно") == [[], []]
