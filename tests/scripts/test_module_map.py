"""Карта данных проверяется тем, что она показывает по данному ей коду.

`--check` сторожит всё остальное в этом скрипте: он сравнивает собранное с
записанным, и расхождение видно сразу. Но разбор данных он не сторожит вовсе —
поломка портит обе стороны сравнения одинаково, и карта остаётся «свежей»,
потеряв половину проекта. Так и вышло: фильтр по регистру выбросил из карты все
четырнадцать таблиц схемы, и ни одна проверка этого не заметила."""

import ast

from module_map import assigned, contents


def shown(source: str) -> list[str]:
    return contents(ast.parse(source))


def only(source: str) -> str:
    values = assigned(ast.parse(source).body[0])
    assert len(values) == 1, values
    return values[0][1]


def test_lowercase_name_is_not_hidden():
    """Таблицы схемы объявлены строчными, и отбор по регистру выбрасывал их
    все — то есть ровно тот случай, ради которого карта данных заведена."""
    lines = shown("item = Table('item', metadata)\nMAX = 5\n")

    assert any("`item`" in line for line in lines)
    assert any("`MAX`" in line for line in lines)


def test_chained_and_unpacked_names_all_get_written():
    """`A = B = 1` — это два объявления. Потерянное второе читается как «его
    нет», а не как «мы его не разобрали»."""
    assert [name for name, _ in assigned(ast.parse("A = B = 1").body[0])] == ["A", "B"]
    assert [name for name, _ in assigned(ast.parse("A, B = 1, 2").body[0])] == ["A", "B"]


def test_field_carries_its_type():
    """По типу поля и узнаётся второй такой же класс: имена у них разные."""
    lines = shown("class Rating:\n    score: float | None\n")

    assert "  - `score: float | None`" in lines


def test_size_of_a_table_is_told_not_its_content():
    assert only("TAGS = {'a': 1, 'b': 2, 'c': 3}") == "словарь из 3"
    assert only("PARTS = ('a', 'b')") == "набор из 2"


def test_size_admits_what_it_could_not_count():
    """Раскрытое внутри не пересчитать, и молча называть неполный размер —
    врать: два справочника сравнивают как раз по размеру."""
    assert only("MORE = {**BASE, 'x': 1}") == "словарь из 1 и раскрытых"
    assert only("MORE = [*PARTS, 'z']") == "набор из 1 и раскрытых"


def test_long_value_is_cut_and_says_so():
    assert only(f"LONG = '{'x' * 200}'").endswith("…")


def test_data_hidden_behind_a_condition_is_still_data():
    lines = shown("if TYPE_CHECKING:\n    ALIAS = 'x'\n")

    assert any("`ALIAS`" in line for line in lines)


def test_nested_class_shows_its_own_fields():
    lines = shown("class Outer:\n    class Inner:\n        kind: str\n")

    assert any("class Inner" in line for line in lines)
    assert any("`kind: str`" in line for line in lines)


def test_class_without_data_is_not_mentioned():
    """Имя такого класса уже названо картой модулей, и повтор её раздувает."""
    assert shown("class Empty:\n    def work(self) -> None:\n        return None\n") == []


def test_surface_is_not_repeated_from_the_other_map():
    assert shown("__all__ = ['A', 'B']\n") == []
