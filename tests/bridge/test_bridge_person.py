"""Мост: выдача по клику на имя — тот же поиск, но одной заявкой.

Отдельным модулем от строки поиска: у клика второго шага нет вовсе — обе
половины приезжают собранными, — и файл строки перевалил предел в пятьсот
строк."""

from datetime import timedelta

from backend.model import ExternalSearch, Kind, Reason, Refusal
from bridge.search import Search
from tests.bridge.conftest import a_view


def test_a_person_search_is_remembered_like_any_other(spy, asked):
    """Выдача по человеку — обычная выдача поиска, и добавить из неё карточку
    можно тем же жестом: значит и помнить её надо тем же способом."""
    answers, _ = asked
    answers["finder.by_entity"] = ExternalSearch(views=(a_view("1"),),
                                                 refusals=())
    answers["loader.ensure"] = 12

    search = Search(spy)
    answer = search.by_person(1, "people", 9, "movie")

    assert answer["ok"]["views"][0]["source_id"] == "1"
    assert search.ensure(1, "tmdb", "1") == {"ok": {"outcome": "found",
                                                    "value": 12}}


def test_a_second_step_after_a_click_gets_nothing(spy, asked):
    """У клика по имени второго шага нет: обе половины приезжают собранными, и
    строку запроса он не запоминает. Позванный с его номером `external`
    разворачивал бы пустую память — исключением, и уже за пределами заявки, то
    есть через границу потоков, где ловить его некому."""
    answers, log = asked
    answers["finder.by_entity"] = ExternalSearch(views=(a_view("1"),),
                                                 refusals=())

    search = Search(spy)
    search.by_person(1, "people", 9, "movie")

    assert search.external(1) == {"fail": "stale"}
    assert [name for name, _, _ in log] == ["finder.by_entity"]


def test_a_person_search_carries_the_kind_as_a_kind(spy, asked):
    """Перевод строки в тип идёт внутри заявки: снаружи оболочки он ушёл бы
    исключением через границу потоков, где ловить его некому. И вкладка —
    первичный фильтр: во вкладке фильмов сериалов не бывает нигде."""
    answers, log = asked
    answers["finder.by_entity"] = ExternalSearch(views=(), refusals=())

    assert Search(spy).by_person(1, "people", 9, "книги")["fail"] == "broken"
    assert log == []

    Search(spy).by_person(1, "companies", 9, "game")
    name, args, _ = log[0]
    assert name == "finder.by_entity"
    assert args == ("companies", 9, Kind.GAME)


def test_a_refusal_of_a_person_search_travels_as_a_field(spy, asked):
    """Половины приезжают собранными, и отказ у них тот же полем ответа:
    второго канала у границы потоков нет."""
    answers, _ = asked
    answers["finder.by_entity"] = ExternalSearch(
        views=(),
        refusals=(Refusal(source="tmdb", reason=Reason.QUOTA,
                          retry_after=timedelta(seconds=60)),))

    answer = Search(spy).by_person(1, "people", 9, "movie")

    assert answer["ok"]["refusals"][0]["reason"] == "quota"
    assert answer["ok"]["refusals"][0]["retry_after"] == 60.0


def test_a_person_search_is_cancellable_like_the_string_one(spy, asked):
    """Клик по второму имени обязан отменить первый: без номера выдача
    неотменяема, и приехать могла бы чужая."""
    answers, _ = asked
    answers["finder.by_entity"] = ExternalSearch(views=(), refusals=())

    Search(spy).by_person(7, "people", 9, "movie")

    assert spy.ops == [7]
