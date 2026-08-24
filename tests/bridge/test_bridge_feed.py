"""Мост: лента — страницы разделов и гистограмма."""

from backend.model import Kind, Section, Sort
from bridge.feed import FeedBridge
from tests.builders import an_item

WISHED = {
    "section": "wishlist",
    "kind": "game",
    "filters": {"tag_ids": [3], "excluded_genre_ids": [7]},
    "order": {"key": "added_at", "descending": True},
}


def test_the_request_is_assembled_from_what_the_page_holds(spy, asked):
    """Собирать `Feed` на стороне JS значило бы объявить те же поля второй раз."""
    answers, log = asked
    answers["feed.page"] = []

    FeedBridge(spy).page(1, WISHED, 0, 50)

    name, args, _ = log[0]
    assert name == "feed.page"
    feed = args[0]
    assert feed.section is Section.WISHLIST
    assert feed.kind is Kind.GAME
    assert feed.order.key is Sort.ADDED_AT
    assert feed.order.descending is True


def test_the_side_of_the_order_survives_the_way(spy, asked):
    """Сторона перебирается вместе с критерием, и «сначала худшие» обязано
    доехать: умолчание у `Order` — сверху то, чего больше."""
    answers, log = asked
    answers["feed.page"] = []

    FeedBridge(spy).page(1, {**WISHED, "order": {"key": "score",
                                                 "descending": False}}, 0, 50)

    assert log[0][1][0].order.descending is False


def test_three_states_of_a_filter_row_become_two_tuples(spy, asked):
    """Не выбран, включён, исключён: исключение сильнее включения, и вычитается
    оно последним — это уже работа базы."""
    answers, log = asked
    answers["feed.page"] = []

    FeedBridge(spy).page(1, WISHED, 0, 50)

    filters = log[0][1][0].filters
    assert filters.tag_ids == (3,)
    assert filters.excluded_genre_ids == (7,)
    assert filters.genre_ids == ()


def test_all_twelve_kinds_of_filter_reach_the_backend(spy, asked):
    """Признаков шесть — метки, жанры, общая оценка и три шкалы игры, — и у
    каждого две половины, включённая и исключённая. Забытый в списке моста
    признак просто перестал бы работать, и молча: отбор по нему не доехал бы до
    базы вовсе.

    Значения у всех разные нарочно: с одинаковыми перепутанные местами половины
    были бы неотличимы, и исключение уехало бы вычитать по чужой шкале."""
    answers, log = asked
    answers["feed.page"] = []
    chosen = {"tag_ids": [1], "genre_ids": [2], "scores": [3],
              "visual": [4], "narrative": [5], "gameplay": [6],
              "excluded_tag_ids": [7], "excluded_genre_ids": [8],
              "excluded_scores": [9], "excluded_visual": [10],
              "excluded_narrative": [11], "excluded_gameplay": [12]}

    FeedBridge(spy).page(1, {**WISHED, "filters": chosen}, 0, 50)

    filters = log[0][1][0].filters
    assert (filters.tag_ids, filters.genre_ids, filters.scores) == ((1,), (2,),
                                                                    (3,))
    assert (filters.visual, filters.narrative,
            filters.gameplay) == ((4,), (5,), (6,))
    assert (filters.excluded_tag_ids, filters.excluded_genre_ids,
            filters.excluded_scores) == ((7,), (8,), (9,))
    assert (filters.excluded_visual, filters.excluded_narrative,
            filters.excluded_gameplay) == ((10,), (11,), (12,))


def test_a_missing_filter_means_no_filter(spy, asked):
    """Страница шлёт только то, что человек тронул: неназванный признак — это
    отсутствие отбора, а не пустой набор, и падать на его отсутствии нельзя."""
    answers, log = asked
    answers["feed.page"] = []

    FeedBridge(spy).page(1, {"section": "rated", "kind": "movie",
                             "filters": {"tag_ids": [3]},
                             "order": {"key": "score", "descending": True}}, 0, 50)

    filters = log[0][1][0].filters
    assert filters.tag_ids == (3,)
    assert filters.scores == ()


def test_paging_carries_the_offset_and_the_size(spy, asked):
    """Лента растёт порциями и своей полной длины не знает. Размер порции —
    довод, а не литерал моста: назначает его страница."""
    answers, log = asked
    answers["feed.page"] = []

    FeedBridge(spy).page(1, WISHED, 100, 25)

    _, args, kwargs = log[0]
    assert (args[1:], kwargs) in (((100, 25), {}), ((), {"offset": 100,
                                                         "limit": 25}))


def test_all_three_ways_into_the_feed_carry_the_number(spy, asked):
    """Смена фильтра или сортировки заводит новый запрос, и ответ прежнего
    приезжать не должен — ни страницей карточек, ни столбцами гистограммы.
    Гасят устаревшее по номеру, и без него лента неотменяема."""
    answers, _ = asked
    answers["feed.page"] = []
    answers["feed.views_of"] = []
    answers["feed.histogram"] = None

    feed = FeedBridge(spy)
    feed.page(4, WISHED, 0, 50)
    feed.views_of(5, [12])
    feed.histogram(6, "game", {})

    assert spy.ops == [4, 5, 6]


def test_one_card_is_reread_by_the_same_door(spy, asked):
    """Точечное обновление после правки — тот же `views_of`, а не второй адрес."""
    answers, log = asked
    answers["feed.views_of"] = []

    FeedBridge(spy).views_of(1, [12])

    assert log[0] == ("feed.views_of", ([12],), {})


def test_the_synopsis_of_one_card_goes_by_its_number(spy, asked):
    """Синопсис лента не возит — его спрашивают на показанную карточку, поштучно
    (см. `view_from_item`). Своей ручки у бэкенда под это нет: строку по номеру
    читает `library.get`, тот же, которым правка карточки кладётся поверх."""
    answers, log = asked
    answers["library.get"] = an_item("157336", "Дитя человеческое",
                                     synopsis="про восстание")

    answer = FeedBridge(spy).synopsis(7, 12)

    assert log[0] == ("library.get", (12,), {})
    assert answer == {"ok": "про восстание"}
    assert spy.ops == [7], "без номера ушедшую операцию нечем гасить"


def test_the_synopsis_of_a_card_that_is_gone_is_empty(spy, asked):
    """Карточку могли удалить ровно между показом и вопросом о ней: показ из-за
    этого падать не должен — синопсиса просто нет."""
    answers, _ = asked
    answers["library.get"] = None

    assert FeedBridge(spy).synopsis(7, 12) == {"ok": ""}


def test_the_histogram_uses_the_same_filters(spy, asked):
    """Гистограмма строится по тому же отфильтрованному набору, что и разделы с
    карточками, — иначе отфильтрованную её не увидеть никогда."""
    answers, log = asked
    answers["feed.histogram"] = None

    FeedBridge(spy).histogram(1, "game", {"tag_ids": [3]})

    name, args, _ = log[0]
    assert name == "feed.histogram"
    assert args[0] is Kind.GAME
    assert args[1].tag_ids == (3,)


def test_a_broken_request_is_a_failure_not_a_crash(spy, asked):
    """Сборка запроса идёт внутри заявки: неизвестный раздел снаружи оболочки
    ушёл бы исключением через границу потоков, где ловить его некому."""
    _, log = asked

    answer = FeedBridge(spy).page(1, {"section": "любимое", "kind": "movie",
                                      "filters": {},
                                      "order": {"key": "score", "descending": True}}, 0, 50)

    assert answer["fail"] == "broken"
    assert log == []


def test_the_histogram_builds_its_request_inside_the_errand_too(spy, asked):
    """Тот же перенос, что и у страницы: у гистограммы свой перевод типа
    содержимого, и вынести его наружу оболочки — та же поломка."""
    _, log = asked

    assert FeedBridge(spy).histogram(1, "книги", {})["fail"] == "broken"
    assert log == []
