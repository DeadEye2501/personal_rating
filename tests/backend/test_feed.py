"""Страница раздела и перерисовка одной карточки."""

from dataclasses import replace

import pytest

from backend.model import Filters, Kind
from backend.service.library import LibraryService
from backend.storage.repository.tags import TagsRepository
from backend.storage.repository.views import ViewsRepository
from tests.conftest import RATED, rated


@pytest.fixture
async def feed(sessions, sections):
    return LibraryService(sections, ViewsRepository(sessions))


async def test_a_page_keeps_the_order_of_the_section(sessions, feed):
    await rated(sessions, "1", 7.0, title="Средний")
    await rated(sessions, "2", 10.0, title="Лучший")
    await rated(sessions, "3", 3.0, title="Худший")

    page = await feed.page(RATED)

    assert [view.title for view in page] == ["Лучший", "Средний", "Худший"]


async def test_a_page_carries_the_whole_card(sessions, feed):
    item_id = await rated(sessions, "1", 9.0, title="Интерстеллар")
    tags = TagsRepository(sessions)
    tag_id = await tags.create(Kind.MOVIE, "пересмотреть")
    await tags.assign(item_id, tag_id)

    page = await feed.page(RATED)

    assert page[0].rating.score == 9.0
    assert [t.name for t in page[0].tags] == ["пересмотреть"]


async def test_an_empty_section_is_an_empty_page(sessions, feed):
    assert await feed.page(RATED) == []


async def test_a_portion_is_fifty_and_it_is_applied(sessions, feed):
    """Лента читается с диска и стоит дёшево — порция больше, чем у поиска.

    Пятьдесят литералом, а не через `PAGE_SIZE`: константа по обе стороны
    проверки делает её нечувствительной к смене числа, а имя теста обещает именно
    пятьдесят. Заводим на одну карточку больше, чтобы порция была видна."""
    for number in range(51):
        await rated(sessions, str(number), 8.0)

    page = await feed.page(RATED)

    assert len(page) == 50


async def test_the_next_portion_continues_the_previous(sessions, feed):
    for number in range(5):
        await rated(sessions, str(number), 10.0 - number)

    first = await feed.page(RATED, offset=0, limit=2)
    second = await feed.page(RATED, offset=2, limit=2)

    assert [v.title for v in first] == ["Фильм 0", "Фильм 1"]
    assert [v.title for v in second] == ["Фильм 2", "Фильм 3"]


class Forgetful(ViewsRepository):
    """Сборка карточек, потерявшая одну. Так бывает по-настоящему: между
    запросом номеров и сборкой карточек человек успел удалить карточку, а
    запросы эти идут разными сессиями."""

    def __init__(self, sessions, lost: int) -> None:
        super().__init__(sessions)
        self._lost = lost

    async def views_for(self, item_ids: list[int]) -> dict:
        found = await super().views_for(item_ids)
        found.pop(self._lost, None)
        return found


async def test_a_card_lost_between_the_two_queries_drops_out(sessions, sections):
    """Страница приходит без неё, а не падает целиком: ронять ленту из-за одной
    исчезнувшей карточки незачем."""
    lost_id = await rated(sessions, "1", 10.0, title="Удалённый")
    await rated(sessions, "2", 9.0, title="Оставшийся")
    feed = LibraryService(sections, Forgetful(sessions, lost_id))

    page = await feed.page(RATED)

    assert [view.title for view in page] == ["Оставшийся"]


async def test_a_page_asks_with_the_filters_it_was_given(sessions, feed):
    """Фильтры едут в запрос целиком: сервис их не разбирает и не теряет."""
    tags = TagsRepository(sessions)
    tagged_id = await rated(sessions, "1", 7.0, title="С меткой")
    await rated(sessions, "2", 9.0, title="Без метки")
    tag_id = await tags.create(Kind.MOVIE, "пересмотреть")
    await tags.assign(tagged_id, tag_id)

    page = await feed.page(replace(RATED, filters=Filters(tag_ids=(tag_id,))))

    assert [view.title for view in page] == ["С меткой"]


async def test_the_histogram_asks_with_the_filters_it_was_given(sessions, feed):
    """Столбцы считаются по тому же отобранному набору, что и страница."""
    tags = TagsRepository(sessions)
    tagged_id = await rated(sessions, "1", 7.0)
    await rated(sessions, "2", 9.0)
    tag_id = await tags.create(Kind.MOVIE, "пересмотреть")
    await tags.assign(tagged_id, tag_id)

    histogram = await feed.histogram(Kind.MOVIE, Filters(tag_ids=(tag_id,)))
    counts = {b.score: b.count for b in histogram.buckets}

    assert (counts[7], counts[9]) == (1, 0)
    assert histogram.total == 1


async def test_the_histogram_goes_through_the_same_service(sessions, feed):
    await rated(sessions, "1", 9.0, title="Интерстеллар")

    histogram = await feed.histogram(Kind.MOVIE, Filters())

    assert len(histogram.buckets) == 10
    assert next(b.count for b in histogram.buckets if b.score == 9) == 1
    assert (histogram.total, histogram.average) == (1, 9.0)
