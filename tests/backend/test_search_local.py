"""Поиск по своей базе — единственный, который работает без сети."""

from datetime import timedelta

import pytest

from backend.model import Kind, PersonRole
from backend.storage.repository.credits import people
from backend.storage.repository.tags import TagsRepository
from tests.conftest import MOMENT, rated
from tests.wiring import search_service


@pytest.fixture
async def search(sessions):
    """Реестр подставной и пустой: `local()` в сеть не ходит вовсе, а поднимать
    ради него шесть настоящих клиентов со своими SSL-контекстами — впустую."""
    return search_service(sessions)


async def test_a_substring_is_enough(sessions, search):
    await rated(sessions, "157336", None, title="Интерстеллар")

    found = await search.local(Kind.MOVIE, "теллар")

    assert [view.title for view in found] == ["Интерстеллар"]


async def test_the_case_does_not_matter_in_russian(sessions, search):
    """Встроенный в SQLite lower() умеет только ASCII: без своей функции русские
    названия не совпали бы никогда."""
    await rated(sessions, "157336", None, title="Интерстеллар")

    found = await search.local(Kind.MOVIE, "ИНТЕРСТЕЛЛАР")

    assert len(found) == 1


async def test_the_original_title_is_searched_too(sessions, search):
    await rated(sessions, "157336", None, title="Интерстеллар",
                original_title="Interstellar")

    found = await search.local(Kind.MOVIE, "stellar")

    assert len(found) == 1


async def test_the_type_of_content_never_mixes(sessions, search):
    await rated(sessions, "157336", None, title="Интерстеллар")
    await rated(sessions, "292030", None, title="Интерстеллар: игра",
                kind=Kind.GAME)

    found = await search.local(Kind.MOVIE, "Интерстеллар")

    assert len(found) == 1


async def test_the_games_are_searched_by_the_same_call(sessions, search):
    """Тип содержимого приходит параметром, а не зашит: с зашитым кино раздел
    игр не находил бы ничего, и все прочие проверки этого не заметили бы."""
    await rated(sessions, "292030", None, title="The Witcher 3", kind=Kind.GAME)
    await rated(sessions, "157336", None, title="Ведьмак: фильм")

    found = await search.local(Kind.GAME, "witcher")

    assert [view.title for view in found] == ["The Witcher 3"]


async def test_a_percent_sign_is_a_letter_and_not_a_wildcard(sessions, search):
    """Иначе запрос «%» вывалил бы всю библиотеку.

    Человек на карточке стоит нарочно: веток отбора четыре — два названия и два
    состава, — и без связи ветка состава в этом сценарии не срабатывает вовсе.
    Экранирование там своё, забыть его можно отдельно."""
    item_id = await rated(sessions, "157336", None, title="Интерстеллар")
    crew = people(sessions)
    await crew.attach(item_id, await crew.create_manual("Кристофер Нолан"),
                      PersonRole.DIRECTOR)

    assert await search.local(Kind.MOVIE, "%") == []


async def test_an_underscore_is_a_letter_too(sessions, search):
    """Второй знак подстановки LIKE. `%` гасится тем же `autoescape`, но
    выпиши экранирование руками — и забыть можно ровно этот."""
    await rated(sessions, "157336", None, title="Интерстеллар")

    assert await search.local(Kind.MOVIE, "_") == []


async def test_the_found_cards_are_whole(sessions, search):
    """Своя половина приезжает со своей оценкой, метками и закладкой. Иначе
    показывать её впереди чужой было бы незачем."""
    item_id = await rated(sessions, "157336", 9.0, title="Интерстеллар")
    tags = TagsRepository(sessions)
    tag_id = await tags.create(Kind.MOVIE, "пересмотреть")
    await tags.assign(item_id, tag_id)

    found = await search.local(Kind.MOVIE, "Интер")

    assert found[0].item_id == item_id
    assert found[0].rating.score == 9.0
    assert [t.name for t in found[0].tags] == ["пересмотреть"]


async def test_an_empty_query_finds_nothing(sessions, search):
    """До первого запроса лента пуста; пустой запрос — это не «показать всё»."""
    await rated(sessions, "157336", None, title="Интерстеллар")

    assert await search.local(Kind.MOVIE, "   ") == []


async def test_the_alphabet_orders_the_found(sessions, search):
    """Порядок устойчивый и не зависит от того, в каком порядке карточки
    заводились: иначе одна и та же выдача перетасовывалась бы между запросами."""
    await rated(sessions, "1", None, title="Яблоко")
    await rated(sessions, "2", None, title="Автобус")

    found = await search.local(Kind.MOVIE, "о")

    assert [view.title for view in found] == ["Автобус", "Яблоко"]


async def test_no_more_than_a_portion_comes_back(sessions, search):
    """Ровно страница выдачи TMDB: одна порция стоит одного запроса.

    Двадцать литералом, а не через `SEARCH_SIZE`: константа по обе стороны
    проверки переезжает вместе с ней и смены числа не заметит."""
    for number in range(25):
        await rated(sessions, str(number), None, title=f"Фильм {number}")

    found = await search.local(Kind.MOVIE, "Фильм")

    assert len(found) == 20


async def test_the_search_does_not_touch_the_clock(sessions, search):
    """Своя выдача обходится без сети и без времени: `synced_at` карточки в
    поиске не участвует вовсе.

    Отметки разнесены на годы: с одной карточкой любой фильтр по свежести,
    заведённый в запросе, прошёл бы молча — умолчание помощника и так свежее."""
    await rated(sessions, "157336", None, title="Интерстеллар свежий",
                synced_at=MOMENT)
    await rated(sessions, "27205", None, title="Интерстеллар давний",
                synced_at=MOMENT - timedelta(days=4000))

    found = await search.local(Kind.MOVIE, "Интерстеллар")

    # Набор, а не порядок: порядок здесь алфавитный и сторожится соседним тестом,
    # а падение этого должно говорить про свежесть — что давняя карточка из
    # выдачи не выпала.
    assert {view.title for view in found} == {
        "Интерстеллар давний", "Интерстеллар свежий"
    }
    # И число: множество проглотило бы строку, размножившуюся соединением.
    assert len(found) == 2
