"""Сборники в выдачу не попадают — кроме того, который спросили прямо.

Сборник это несколько игр под одной строкой, и показывать его незачем: решение
пользователя 03.08.2026. Исключение одно — слово сборника стоит в самой строке
поиска, и тогда остаётся тот сборник, который спросили.

Что склеивается — `test_merging.py`, кто побеждает — `test_merging_winner.py`."""

import pytest

from backend.model import Source
from backend.service.merging import SETS, merged
from tests.builders import row, titles


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
    «Fallout Collection» есть, а сборника человек не просил — и строка остаётся
    скрытой. Ровно эти строки спека и назвала ценой решения.

    Соседкой взята «Fallout 2», а не «Fallout»: с одноимённой сборник исчезал
    бы и при снятой проверке «сборник назвали», потому что склейка убрала бы
    его как одетую строку. Ключи тут разные — `fallout` против `fallout 2`, —
    поэтому спрятать сборник может только сам отсев."""
    steam = [row(Source.STEAM, "1", "Fallout 2"),
             row(Source.STEAM, "2", "Fallout Collection")]

    assert titles(merged([steam], "fallout")) == ["Fallout 2"]


# Слова сборника поимённо. Наблюдалось три из семи, а цена ошибки односторонняя
# и тяжелее, чем у изданий: лишнее слово **скрывает настоящие игры навсегда** —
# спека уже назвала пятнадцать таких строк ценой решения. Два слова русские, и
# источник с русскими названиями появился тем же планом, что и они.
FROZEN_SETS = ("bundle", "collection", "trilogy", "anthology", "антология",
               "коллекция", "compilation")


def test_the_words_of_a_compilation_did_not_drift():
    assert SETS == FROZEN_SETS


@pytest.mark.parametrize("word", FROZEN_SETS)
def test_each_word_of_a_compilation_hides_its_row(word):
    """Снимок сторожит состав, а это — что каждое слово в нём работает.

    Запрос нарочно не содержит слова сборника: иначе сработало бы исключение
    «остался тот, который спросили», и строка осталась бы законно."""
    steam = [row(Source.STEAM, "1", "Fallout 2"),
             row(Source.STEAM, "2", f"Fallout {word}")]

    assert titles(merged([steam], "fallout")) == ["Fallout 2"]
