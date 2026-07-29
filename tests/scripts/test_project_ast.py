"""Разбор проекта проверяется тем, что он вычитывает из данного ему кода."""

import ast

from project_ast import declarations


def indexed(source: str, path: str = "a.py") -> dict[str, str]:
    return declarations([(path, ast.parse(source), 0)])


def test_declaration_is_named_by_its_owner_too():
    """Вердикт ссылается на объявление именем: у метода оно неполно без класса,
    и два `_read` в разных классах слились бы в одну ссылку."""
    index = indexed("class Store:\n    def read(self):\n        return 1\n")

    assert "a.py:Store.read" in index


def test_nested_declarations_are_indexed():
    index = indexed("def outer():\n    def inner():\n        return 1\n")

    assert "a.py:outer.inner" in index


def test_a_changed_signature_changes_the_stamp():
    """Сменившийся тип аргумента меняет дело так же, как переписанное тело,
    поэтому отпечаток берётся с объявления целиком, а не с одного тела."""
    before = indexed("def one(value: int) -> int:\n    return value\n")
    after = indexed("def one(value: str) -> str:\n    return value\n")

    assert before["a.py:one"] != after["a.py:one"]


def test_same_code_gives_the_same_stamp():
    """Иначе вердикты гасли бы на каждой сборке и проверка утонула бы в шуме."""
    source = "def one():\n    return 1\n"

    assert indexed(source) == indexed(source)


def test_a_field_without_a_value_still_gets_a_stamp():
    """У поля датакласса значения нет вовсе, а отпечаток нужен: пустой не
    отличить от «ещё не заверено», и сборка дописывала бы пустые кавычки при
    каждом прогоне, пока не разломает строку вердикта."""
    index = indexed("class Rating:\n    score: float | None\n    review: str = ''\n")

    assert index["a.py:Rating.score"]
    assert index["a.py:Rating.review"]


def test_a_field_of_another_type_is_another_field():
    """Сменившийся тип поля меняет дело так же, как переписанное тело."""
    before = indexed("class Rating:\n    score: float\n")
    after = indexed("class Rating:\n    score: int\n")

    assert before["a.py:Rating.score"] != after["a.py:Rating.score"]
