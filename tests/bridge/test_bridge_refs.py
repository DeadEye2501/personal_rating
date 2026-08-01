"""Мост: справочники — жанры, люди, студии."""

import pytest

from backend.model import GenreKind, PersonRole
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


def test_the_next_portion_is_asked_by_its_offset(spy, asked):
    """Список догружается прокруткой, и страница называет, откуда продолжать.
    Потеряйся смещение — вторая порция приехала бы первой же, и список крутился
    бы по кругу из одних и тех же имён."""
    answers, log = asked
    answers["people.suggest"] = []

    Refs(spy).suggest("people", "Нолан", 20)

    assert log[0][1:] == (("Нолан",), {"offset": 20})


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


def test_genres_of_a_card_are_written_as_a_whole(spy, asked):
    """Набор жанров правится целиком, а не по одному: сличать построчно значило
    бы решать за страницу, что именно человек поменял."""
    answers, log = asked
    answers["genres.set_for_item"] = None

    Refs(spy).set_genres(7, [3, 9])

    assert log[0] == ("genres.set_for_item", (7, [3, 9]), {})


@pytest.mark.parametrize(("domain", "asked_name"),
                         [("people", "people.detach_all"),
                          ("companies", "companies.detach_all")])
def test_the_cast_is_dropped_from_the_shelf_it_lies_on(spy, asked, domain,
                                                       asked_name):
    """Состав правится тем же приёмом: снять всё и расставить заново. Домены
    проверяются оба — сняв людей вместо студий, страница потеряла бы состав
    молча."""
    answers, log = asked
    answers[asked_name] = None

    Refs(spy).detach_all(domain, 7)

    assert [name for name, _, _ in log] == [asked_name]


def test_a_role_reaches_the_base_as_its_own_type(spy, asked):
    """Роль приходит строкой, а база держит перечисление. Перевод стоит внутри
    заявки: снаружи оболочки негодная роль ушла бы исключением через границу
    потоков, где ловить его некому."""
    answers, log = asked
    answers["people.attach"] = None

    Refs(spy).attach("people", 7, 12, "director", 0)

    assert log[0] == ("people.attach", (7, 12, PersonRole.DIRECTOR, 0), {})


def test_a_role_the_shelf_does_not_keep_is_a_failure(spy, asked):
    """Студия режиссёром не бывает: `CompanyRole` такого значения не знает, и
    отказ обязан прийти отказом, а не вечным промисом."""
    _, log = asked

    assert Refs(spy).attach("companies", 7, 12, "director", 0)["fail"] == "broken"
    assert log == []


def test_an_unknown_set_of_genres_is_a_failure_too(spy, asked):
    """Разбор довода идёт внутри заявки: снаружи оболочки он ушёл бы
    исключением через границу потоков. До бэкенда при этом не доходит ничего —
    иначе разбор уехал бы туда, а тут проверяется место, где он стоит."""
    _, log = asked

    assert Refs(spy).genres("книги")["fail"] == "broken"
    assert log == []
