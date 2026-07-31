"""То, что не пролезает обратно через JSON, мост помнит у себя."""

from bridge.kept import Kept


def test_what_was_kept_comes_back():
    kept = Kept()
    kept.put(1, ["выдача"])
    assert kept.taken(1) == ["выдача"]


def test_a_stale_number_gets_nothing():
    """Страница набрала новый запрос, пока летел старый: второй шаг старой
    операции обязан уйти ни с чем, а не подставить чужую выдачу.

    Здесь же видно, что помнится ровно одно значение: словарь по номеру протекал
    бы на каждой брошенной операции, а брошенных больше, чем доведённых."""
    kept = Kept()
    kept.put(1, ["старое"])
    kept.put(2, ["новое"])

    assert kept.taken(1) is None
    assert kept.taken(2) == ["новое"]


def test_nothing_kept_is_not_a_failure():
    """Второй шаг без первого — обычное дело: операцию отменили."""
    assert Kept().taken(1) is None
