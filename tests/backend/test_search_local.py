import pytest

from backend.model import Kind
from backend.service.search import SEARCH_SIZE, SearchService
from backend.storage.repository.library import LibraryRepository
from backend.storage.repository.tags import TagsRepository
from backend.storage.repository.views import ViewsRepository
from tests.conftest import MOMENT, rated


@pytest.fixture
async def search(sessions):
    """Источники сюда не передаются: `local()` в сеть не ходит, и добавит их
    задача о внешнем поиске — вместе с тем, кто их спрашивает."""
    return SearchService(LibraryRepository(sessions), ViewsRepository(sessions))


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
    """Иначе запрос «%» вывалил бы всю библиотеку."""
    await rated(sessions, "157336", None, title="Интерстеллар")

    assert await search.local(Kind.MOVIE, "%") == []


async def test_an_underscore_is_a_letter_too(sessions, search):
    """Второй знак подстановки LIKE. `%` гасится тем же `autoescape`, но
    выпиши экранирование руками — и забыть можно ровно этот."""
    await rated(sessions, "157336", None, title="Интерстеллар")

    assert await search.local(Kind.MOVIE, "_") == []


async def test_the_found_cards_are_whole(sessions, search):
    """Своё стоит в общей выдаче на своём месте — но со своей оценкой, метками
    и закладкой. Иначе показывать его вперемешку с чужим незачем."""
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
    """Ровно страница выдачи TMDB: одна порция стоит одного запроса. Константу
    мало объявить — без проверки, что её применяют, её можно поменять на любую,
    и никто не заметит."""
    assert SEARCH_SIZE == 20
    for number in range(SEARCH_SIZE + 5):
        await rated(sessions, str(number), None, title=f"Фильм {number}")

    found = await search.local(Kind.MOVIE, "Фильм")

    assert len(found) == SEARCH_SIZE


async def test_the_search_does_not_touch_the_clock(sessions, search):
    """Своя выдача обходится без сети и без времени: `synced_at` карточки в
    поиске не участвует вовсе."""
    await rated(sessions, "157336", None, title="Интерстеллар",
                synced_at=MOMENT)

    assert len(await search.local(Kind.MOVIE, "Интер")) == 1
