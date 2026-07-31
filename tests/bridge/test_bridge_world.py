"""Мост: внешний мир — привязка, перезапрос, оценки агрегаторов."""

from datetime import datetime
from types import SimpleNamespace

from backend.model import ItemExists, Kind, Missing, RatingSource
from bridge.world import World


def test_a_pasted_link_is_parsed_without_the_network(spy, asked):
    """Галочка появляется, когда адрес похож на разобранный, — это чистая
    функция, и второй регулярки на тот же адрес быть не должно."""
    _, log = asked

    answer = World(spy).parse("https://www.themoviedb.org/movie/157336-inter",
                              None)

    assert answer["ok"]["source"] == "tmdb"
    assert answer["ok"]["source_id"] == "157336"
    assert answer["ok"]["kind"] == "movie"
    assert log == []


def test_something_that_is_not_a_link_is_not_a_failure(spy, asked):
    """Человек ещё печатает: непохожее на адрес — это «пока нет», а не отказ."""
    assert World(spy).parse("одис", None) == {"ok": None}


def test_the_card_for_a_link_is_kept_not_sent_back(spy, asked):
    """`SourceCard` уезжает словарём, а `linker.link` требует датакласс:
    возить его туда и обратно значило бы объявить те же поля второй раз."""
    answers, log = asked
    answers["loader.card_for_link"] = "карточка"
    answers["linker.link"] = None

    world = World(spy)
    assert world.card_for_link(1, "themoviedb.org/movie/157336", None) == {
        "ok": {"outcome": "found", "value": "карточка"}}

    before = datetime.now()
    world.link(1, 12, False)
    after = datetime.now()

    name, args, kwargs = log[1]
    assert name == "linker.link"
    assert args[0] == 12
    assert args[1] == "карточка"
    assert before <= args[2] <= after
    assert kwargs == {"overwrite": False}
    assert spy.ops == [1, 1]
    assert log[0][1][0].source_id == "157336"


def test_the_overwrite_box_reaches_the_backend(spy, asked):
    """Галочка «перезаписать данные» — на случай карточки, заведённой на скорую
    руку: без неё внешнее доливает только пустое."""
    answers, log = asked
    answers["loader.card_for_link"] = "карточка"
    answers["linker.link"] = None

    world = World(spy)
    world.card_for_link(1, "themoviedb.org/movie/157336", None)
    world.link(1, 12, True)

    assert log[1][2] == {"overwrite": True}


def test_linking_without_a_kept_card_is_stale(spy, asked):
    assert World(spy).link(1, 12, False) == {"fail": "stale"}


def test_a_taken_identity_is_a_kind_of_failure(spy, asked):
    """Ссылка ведёт на карточку, которая в библиотеке уже есть: дубль завести не
    даём, и говорим об этом.

    Род отказа именно `item-exists`: занятость проверяется до первой записи, и
    привязка поднимает там `ItemExists`. `ExternalIdTaken` до клиента не долетает
    вовсе — его ловит и пишет в лог сам `Enricher`."""
    answers, _ = asked
    answers["loader.card_for_link"] = "карточка"
    answers["linker.link"] = ItemExists("imdb:tt0816692 уже за карточкой 4")

    world = World(spy)
    world.card_for_link(1, "themoviedb.org/movie/157336", None)

    assert world.link(1, 12, False)["fail"] == "item-exists"


def test_a_source_without_that_card_says_missing(spy, asked):
    answers, _ = asked
    answers["loader.card_for_link"] = Missing()

    assert World(spy).card_for_link(1, "themoviedb.org/movie/1", None) == {
        "ok": {"outcome": "missing"}}


def test_an_unparsable_link_never_reaches_the_network(spy, asked):
    _, log = asked

    assert World(spy).card_for_link(1, "одис", None)["fail"] == "bad-link"
    assert log == []


def test_refreshing_a_series_is_silent_when_nothing_was_needed(spy, asked):
    """Клиент не может отличить «перезапросили» от «не понадобилось», и не
    должен: перезапрос идёт по сроку, а решает его бэкенд."""
    answers, log = asked
    answers["series.refresh"] = None

    assert World(spy).refresh_series(1, 12) == {"ok": None}
    assert log == [("series.refresh", (12,), {})]
    assert spy.ops == [1]


def test_enriching_answers_with_what_arrived(spy, asked):
    answers, log = asked
    answers["enricher.enrich"] = []

    World(spy).enrich(1, 12, "movie")

    name, args, _ = log[0]
    assert name == "enricher.enrich"
    assert args[0] == 12
    # Тождеством, а не равенством: тип содержимого — строковое перечисление, и
    # `==` пропустило бы сырую строку, а реестр источников различает его `is`.
    assert args[1] is Kind.MOVIE
    assert spy.ops == [1]


def test_expected_sources_are_known_before_the_network(thread, backend):
    """Под неприехавшую оценку рисуется кружок, и сколько их будет, надо знать
    до ответа сети.

    Единственный метод домена, проверяемый настоящим потоком, а не записывающим
    двойником, и не по прихоти: у бэкенда он **синхронный**, а поток кладёт
    фабрику в `create_task`, который от не-корутины поднимает `TypeError`. Без
    обёртки страница получила бы «непредвиденный сбой» вместо ответа, который
    есть и приезжает мгновенно. Двойник этот стык подменяет: он отдаёт корутину
    на любой вызов, и синхронный метод на нём неотличим от асинхронного."""
    seen = []
    backend.enricher = SimpleNamespace(
        expected=lambda kind: seen.append(kind) or [RatingSource.IMDB,
                                                    RatingSource.KINOPOISK])

    assert World(thread).expected(1, "movie") == {"ok": ["imdb", "kinopoisk"]}
    assert seen == [Kind.MOVIE]


def test_a_foreign_scheme_is_refused(spy, asked, monkeypatch):
    """Адрес приходит со страницы карточки, а `webbrowser` отдаёт строку системе
    как есть: чужая схема — это чужая программа, запущенная с нашими правами.

    Браузер подменён нарочно: сорвись предохранитель — и прогон открывал бы
    проводник на системной папке, а тест всё равно был бы зелёным."""
    opened = []
    monkeypatch.setattr("webbrowser.open", opened.append)

    answer = World(spy).open("file:///C:/Windows/system32")

    assert answer["fail"] == "foreign-scheme"
    assert opened == []


def test_a_page_of_the_source_is_opened_by_the_system_browser(spy, asked,
                                                              monkeypatch):
    """Единственная работающая строка ручки: без неё имя агрегатора на карточке
    стало бы мёртвой кнопкой, и молча."""
    opened = []
    monkeypatch.setattr("webbrowser.open", opened.append)

    assert World(spy).open("https://www.imdb.com/title/tt0816692/") == {
        "ok": None}
    assert opened == ["https://www.imdb.com/title/tt0816692/"]


def test_an_unknown_kind_never_reaches_the_parser(spy, asked):
    """Перевод подсказки тумблера идёт внутри заявки: снаружи оболочки он ушёл
    бы исключением через границу потоков."""
    _, log = asked

    assert World(spy).parse("одис", "книги")["fail"] == "broken"
    assert log == []
