"""Мост: справочники — жанры, люди, студии."""

import pytest

from backend.model import GenreKind
from bridge.refs import Refs


def test_genres_come_for_the_asked_set(spy, asked):
    """Наборов жанров два: кино (фильмы и сериалы делят один) и игры."""
    answers, log = asked
    answers["genres.list_for_kind"] = []

    Refs(spy).genres("game")

    name, args, _ = log[0]
    assert name == "genres.list_for_kind"
    assert args[0] is GenreKind.GAME


@pytest.mark.parametrize(("domain", "asked_name"),
                         [("people", "people.suggest"),
                          ("companies", "companies.suggest")])
def test_the_domain_chooses_the_repository(spy, asked, domain, asked_name):
    """Один класс, два экземпляра: одиннадцать методов писать дважды нельзя, и
    сторожит это привязка, а не набор имён."""
    answers, log = asked
    answers[asked_name] = []

    Refs(spy).suggest(domain, "Нолан")

    assert [name for name, _, _ in log] == [asked_name]
    assert log[0][1] == ("Нолан",)


def test_an_unknown_domain_is_a_failure_not_a_crash(spy, asked):
    """Опечатка на стороне страницы не должна становиться вечным промисом."""
    _, log = asked

    assert Refs(spy).suggest("actors", "Нолан")["fail"] == "broken"
    assert log == []


@pytest.mark.parametrize(("domain", "asked_name"),
                         [("people", "people.create_manual"),
                          ("companies", "companies.create_manual")])
def test_enter_on_nothing_highlighted_creates_a_new_one(spy, asked, domain,
                                                        asked_name):
    """Совпадение имени само по себе не решает ничего: полные тёзки существуют,
    и завести второго Василия Пупкина можно.

    Оба домена проверяются нарочно: люди и студии живут в одной таблице, и
    заведённая руками студия ушла бы в люди молча, с идентичностью человека."""
    answers, log = asked
    answers[asked_name] = 9

    assert Refs(spy).create_person(domain, "Василий Пупкин") == {"ok": 9}
    assert log[0] == (asked_name, ("Василий Пупкин",), {})


def test_an_unknown_set_of_genres_is_a_failure_too(spy, asked):
    """Разбор довода идёт внутри заявки: снаружи оболочки он ушёл бы
    исключением через границу потоков. До бэкенда при этом не доходит ничего —
    иначе разбор уехал бы туда, а тут проверяется место, где он стоит."""
    _, log = asked

    assert Refs(spy).genres("книги")["fail"] == "broken"
    assert log == []
