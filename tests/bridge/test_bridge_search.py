"""Мост: поиск — своё, чужое, складывание, заведение найденного."""

from datetime import timedelta

from backend.model import (
    CardView,
    ExternalSearch,
    Kind,
    Missing,
    Reason,
    Refusal,
    Source,
)
from bridge.search import Search


def a_view(source_id, item_id=None, title="Одиссея", source=Source.TMDB):
    return CardView(kind=Kind.MOVIE, source=source, source_id=source_id,
                    title=title, item_id=item_id)


def test_local_comes_first_and_alone(spy, asked):
    """Ждать сеть, чтобы показать лежащее на диске, незачем."""
    answers, log = asked
    answers["search.local"] = [a_view("1", item_id=5)]

    answer = Search(spy).local(1, "movie", "одиссея")

    assert [name for name, _, _ in log] == ["search.local"]
    assert answer["ok"][0]["item_id"] == 5


def test_external_is_merged_with_what_was_shown(spy, asked):
    """Свой близнец чужого кандидата показывается один раз, и показывается
    именно свой: у него есть оценка, теги и закладка."""
    answers, _ = asked
    answers["search.local"] = [a_view("1", item_id=5)]
    answers["search.external"] = ExternalSearch(
        views=(a_view("1"), a_view("2")), refusals=())

    search = Search(spy)
    search.local(1, "movie", "одиссея")
    answer = search.external(1)

    ids = [view["source_id"] for view in answer["ok"]["views"]]
    assert ids == ["1", "2"]
    assert answer["ok"]["views"][0]["item_id"] == 5


def test_the_local_half_comes_first(spy, asked):
    """Сначала своя половина целиком, потом чужая — правило одно на всю выдачу
    поиска, и живёт оно в `merge_results`."""
    answers, _ = asked
    answers["search.local"] = [a_view("9", item_id=5, title="Только своё")]
    answers["search.external"] = ExternalSearch(views=(a_view("1"),),
                                                refusals=())

    search = Search(spy)
    search.local(1, "movie", "одиссея")

    ids = [view["source_id"]
           for view in search.external(1)["ok"]["views"]]
    assert ids == ["9", "1"]


def test_the_query_is_asked_once(spy, asked):
    """Второй шаг не переспрашивает запрос: разъехаться им было бы нечему —
    мост помнит и тип, и строку."""
    answers, log = asked
    answers["search.local"] = []
    answers["search.external"] = ExternalSearch(views=(), refusals=())

    search = Search(spy)
    search.local(1, "game", "ведьмак")
    search.external(1)

    name, args, _ = log[1]
    assert name == "search.external"
    assert args[0] is Kind.GAME
    assert args[1] == "ведьмак"


def test_an_unknown_kind_is_a_failure_not_a_crash(spy, asked):
    """Перевод запроса в тип идёт внутри заявки: снаружи оболочки он ушёл бы
    исключением через границу потоков, где ловить его некому."""
    _, log = asked

    assert Search(spy).local(1, "книги", "одиссея")["fail"] == "broken"
    assert log == []


def test_both_halves_carry_the_number(spy, asked):
    """Набрал новую строку — старый ответ приезжать не должен, и гасят его по
    номеру: без него поиск неотменяем."""
    answers, _ = asked
    answers["search.local"] = []
    answers["search.external"] = ExternalSearch(views=(), refusals=())

    search = Search(spy)
    search.local(3, "movie", "одиссея")
    search.external(3)

    assert spy.ops == [3, 3]


def test_a_stale_number_gets_nothing(spy, asked):
    """Набрал новый запрос, пока летел старый: старые результаты не затирают
    новые, и второй шаг старой операции обязан уйти ни с чем."""
    answers, _ = asked
    answers["search.local"] = []

    search = Search(spy)
    search.local(1, "movie", "старое")
    search.local(2, "movie", "новое")

    assert search.external(1) == {"fail": "stale"}


def test_a_refusal_of_the_outer_base_travels_as_a_field(spy, asked):
    """Отказ источника — не исключение, а поле в ответе: второго канала у
    границы потоков нет."""
    answers, _ = asked
    answers["search.local"] = []
    answers["search.external"] = ExternalSearch(
        views=(),
        refusals=(Refusal(source="tmdb", reason=Reason.NETWORK,
                          retry_after=timedelta(seconds=15)),))

    search = Search(spy)
    search.local(1, "movie", "одиссея")
    answer = search.external(1)

    assert answer["ok"]["refusals"][0]["reason"] == "network"
    assert answer["ok"]["refusals"][0]["retry_after"] == 15.0


def test_a_candidate_is_added_by_its_pair(spy, asked):
    """Пара «источник + идентификатор» переживает перерисовку выдачи, а номер
    строки — нет. В выдаче лежит тёзка по идентификатору из другого источника:
    иначе половина ключа не сторожилась бы вовсе."""
    answers, log = asked
    answers["search.local"] = [a_view("157336", source=Source.STEAM),
                               a_view("157336")]
    answers["loader.ensure"] = 12

    search = Search(spy)
    search.local(1, "movie", "интерстеллар")
    answer = search.ensure(1, "tmdb", "157336")

    assert answer == {"ok": {"outcome": "found", "value": 12}}
    name, args, _ = log[1]
    assert name == "loader.ensure"
    assert args[0].source_id == "157336"
    assert args[0].source is Source.TMDB
    assert spy.ops == [1, 1]


def test_a_candidate_from_the_outer_half_can_be_added_too(spy, asked):
    """Складывание обязано обновить память: кандидат, приехавший из чужой
    половины, в локальной выдаче не лежал никогда, и без этого добавить
    найденное в TMDB было бы нельзя вовсе."""
    answers, log = asked
    answers["search.local"] = []
    answers["search.external"] = ExternalSearch(views=(a_view("157336"),),
                                                refusals=())
    answers["loader.ensure"] = 12

    search = Search(spy)
    search.local(1, "movie", "интерстеллар")
    search.external(1)

    assert search.ensure(1, "tmdb", "157336") == {"ok": {"outcome": "found",
                                                         "value": 12}}
    assert log[2][1][0].source_id == "157336"


def test_adding_something_that_is_not_in_the_list_is_stale(spy, asked):
    """Выдача не пуста, но названного в ней нет: молча завести первого
    попавшегося значило бы добавить в библиотеку чужую карточку."""
    answers, log = asked
    answers["search.local"] = [a_view("157336")]

    search = Search(spy)
    search.local(1, "movie", "одиссея")

    assert search.ensure(1, "tmdb", "404") == {"fail": "stale"}
    assert [name for name, _, _ in log] == ["search.local"]


def test_a_source_that_lost_the_card_says_so(spy, asked):
    """Исход запроса к источнику — один из трёх, и `Missing` обязан отличаться
    от чего угодно пустого."""
    answers, _ = asked
    answers["search.local"] = [a_view("157336")]
    answers["loader.ensure"] = Missing()

    search = Search(spy)
    search.local(1, "movie", "интерстеллар")

    assert search.ensure(1, "tmdb", "157336") == {
        "ok": {"outcome": "missing"}}
