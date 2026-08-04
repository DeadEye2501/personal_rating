"""Запросы разделов: что раздел показывает, в каком порядке и какой порцией.

Чем набор сужают — в `test_filters.py`: сортировка от фильтра не зависит вовсе,
и проверяются они порознь."""

from dataclasses import replace
from datetime import timedelta

import pytest

from backend.model import Kind, Order, Sort, Source
from backend.storage.repository.library import LibraryRepository
from backend.storage.repository.ratings import RatingsRepository
from backend.storage.repository.wishlist import WishlistRepository
from tests.conftest import MOMENT, RATED, WANTED, an_item


@pytest.fixture
async def library(sessions):
    return LibraryRepository(sessions)


async def test_the_rated_section_shows_only_what_has_a_score(
    sessions, library, sections
):
    rated_id = await library.create(an_item("1", "Оценённый", year=2014))
    await library.create(an_item("2", "Просто лежит", year=2010))
    await RatingsRepository(sessions).set_score(rated_id, 8.0, now=MOMENT)

    found = await sections.ids(RATED, limit=50, offset=0)

    assert found == [rated_id]


async def test_a_card_with_the_score_taken_away_leaves_the_section(
    sessions, library, sections
):
    """Карточка остаётся в базе, но в «Оценённых» ей больше не место."""
    item_id = await library.create(an_item("1", "Оценённый", year=2014))
    ratings = RatingsRepository(sessions)
    await ratings.set_score(item_id, 8.0, now=MOMENT)
    await ratings.clear(item_id)

    found = await sections.ids(RATED, limit=50, offset=0)

    assert found == []


async def test_a_review_without_a_score_is_not_a_rated_card(
    sessions, library, sections
):
    """Состояние достижимое: set_review заводит строку rating со score = NULL.
    Проверять надо именно оценку, а не наличие строки, — иначе карточка с одной
    заметкой попала бы и в «Оценённые», и в гистограмму."""
    item_id = await library.create(an_item("1", "С заметкой", year=2014))
    await RatingsRepository(sessions).set_review(item_id, "надо пересмотреть",
                                                 now=MOMENT)

    found = await sections.ids(RATED, limit=50, offset=0)

    assert found == []


async def test_the_wishlist_shows_what_is_bookmarked(sessions, library, sections):
    wanted_id = await library.create(an_item("1", "Отложенный", year=2024))
    await library.create(an_item("2", "Не отложенный", year=2010))
    await WishlistRepository(sessions).add(wanted_id, now=MOMENT)

    found = await sections.ids(WANTED, limit=50, offset=0)

    assert found == [wanted_id]


async def test_the_type_of_content_never_mixes(sessions, library, sections):
    movie_id = await library.create(an_item("1", "Фильм", year=2014))
    game_id = await library.create(
        an_item("292030", "Игра", kind=Kind.GAME, source=Source.STEAM, year=2015)
    )
    ratings = RatingsRepository(sessions)
    await ratings.set_score(movie_id, 8.0, now=MOMENT)
    await ratings.set_score(game_id, 9.0, now=MOMENT)

    found = await sections.ids(RATED, limit=50, offset=0)

    assert found == [movie_id]


async def test_the_high_scores_come_first(sessions, library, sections):
    """Карточек три, и ожидаемый порядок не совпадает ни с порядком их
    появления, ни с обратным: с двумя любой порядок совпал бы с одним из этих
    двух, и подмена ключа сортировки на номер прошла бы молча."""
    ratings = RatingsRepository(sessions)
    middle_id = await library.create(an_item("1", "Средне", year=2014))
    high_id = await library.create(an_item("2", "Отлично", year=2010))
    low_id = await library.create(an_item("3", "Так себе", year=2001))
    await ratings.set_score(middle_id, 8.0, now=MOMENT)
    await ratings.set_score(high_id, 10.0, now=MOMENT)
    await ratings.set_score(low_id, 5.0, now=MOMENT)

    found = await sections.ids(RATED, limit=50, offset=0)

    assert found == [high_id, middle_id, low_id]


async def test_the_freshly_rated_come_first(sessions, library, sections):
    """Троица в том же порядке, что и у оценок, и по той же причине. Оценки при
    этом идут против времени: с совпадающими двумя ключами сортировка по оценке
    прошла бы здесь молча."""
    ratings = RatingsRepository(sessions)
    middle_id = await library.create(an_item("1", "На днях", year=2014))
    new_id = await library.create(an_item("2", "Только что", year=2010))
    old_id = await library.create(an_item("3", "Давно", year=2001))
    await ratings.set_score(middle_id, 6.0, now=MOMENT - timedelta(days=2))
    await ratings.set_score(new_id, 5.0, now=MOMENT)
    await ratings.set_score(old_id, 9.0, now=MOMENT - timedelta(days=5))

    found = await sections.ids(replace(RATED, order=Order(Sort.RATED_AT)),
                               limit=50, offset=0)

    assert found == [new_id, middle_id, old_id]


async def test_the_newest_by_release_come_first(sessions, library, sections):
    ratings = RatingsRepository(sessions)
    middle_id = await library.create(an_item("1", "Среднее", year=2010))
    new_id = await library.create(an_item("2", "Новое", year=2024))
    old_id = await library.create(an_item("3", "Старое", year=1999))
    for item_id in (middle_id, new_id, old_id):
        await ratings.set_score(item_id, 8.0, now=MOMENT)

    found = await sections.ids(replace(RATED, order=Order(Sort.YEAR)),
                               limit=50, offset=0)

    assert found == [new_id, middle_id, old_id]


async def test_the_freshly_bookmarked_come_first(sessions, library, sections):
    wishlist = WishlistRepository(sessions)
    middle_id = await library.create(an_item("1", "Отложил на днях", year=2014))
    new_id = await library.create(an_item("2", "Отложил только что", year=2010))
    old_id = await library.create(an_item("3", "Отложил давно", year=2001))
    await wishlist.add(middle_id, now=MOMENT - timedelta(days=1))
    await wishlist.add(new_id, now=MOMENT)
    await wishlist.add(old_id, now=MOMENT - timedelta(days=3))

    found = await sections.ids(WANTED, limit=50, offset=0)

    assert found == [new_id, middle_id, old_id]


async def test_a_portion_is_taken_from_the_offset(sessions, library, sections):
    ratings = RatingsRepository(sessions)
    ids = []
    for number in range(5):
        item_id = await library.create(
            an_item(str(number), f"Фильм {number}", year=2000)
        )
        await ratings.set_score(item_id, 10.0 - number, now=MOMENT)
        ids.append(item_id)

    page = await sections.ids(RATED, limit=2, offset=2)

    assert page == ids[2:4]


async def test_equal_scores_are_ordered_by_identifier(sessions, library, sections):
    """Второй ключ сортировки. Без него одна и та же карточка попала бы и в
    первую порцию, и во вторую, а соседняя — ни в одну.

    Годы идут против номеров нарочно: при равных оценках без второго ключа
    порядок задаёт индекс, по которому планировщик пошёл за `kind`, а таких
    индексов в схеме два. По `ix_item_kind` получается порядок номеров, и потеря
    ключа не видна; по `ix_item_kind_year` — порядок года, и тогда этот тест
    краснеет. Оба выбора замерены на одной и той же схеме, и это и есть довод
    оставить `ORDER BY` в коде: полагаться на выбор планировщика нельзя."""
    ratings = RatingsRepository(sessions)
    ids = []
    for number in range(6):
        item_id = await library.create(
            an_item(str(number), f"Фильм {number}", year=2005 - number)
        )
        await ratings.set_score(item_id, 8.0, now=MOMENT)
        ids.append(item_id)

    first = await sections.ids(RATED, limit=3, offset=0)
    second = await sections.ids(RATED, limit=3, offset=3)

    assert first == sorted(ids)[:3]
    assert second == sorted(ids)[3:]


async def test_equal_scores_are_broken_by_the_time_of_rating(
    sessions, library, sections
):
    """Ничью основного критерия разбивает дата раздела, свежим вверх.

    Ожидаемый порядок не совпадает ни с порядком появления карточек, ни с
    обратным: с двумя любой порядок совпал бы с одним из них, и снятый ключ
    прошёл бы молча — порядок задал бы номер."""
    ratings = RatingsRepository(sessions)
    middle_id = await library.create(an_item("1", "На днях", year=2014))
    new_id = await library.create(an_item("2", "Только что", year=2010))
    old_id = await library.create(an_item("3", "Давно", year=2001))
    await ratings.set_score(middle_id, 8.0, now=MOMENT - timedelta(days=2))
    await ratings.set_score(new_id, 8.0, now=MOMENT)
    await ratings.set_score(old_id, 8.0, now=MOMENT - timedelta(days=5))

    found = await sections.ids(RATED, limit=50, offset=0)

    assert found == [new_id, middle_id, old_id]


async def test_equal_titles_are_broken_by_the_time_of_bookmarking(
    sessions, library, sections
):
    """То же в отложенном, и дата там своя — закладки, а не оценки.

    Ничья по названию достижима: одноимённых карточек схема не запрещает, а в
    отложенном критериев всего два, и второй — как раз алфавит."""
    wishlist = WishlistRepository(sessions)
    middle_id = await library.create(an_item("1", "Тезис", year=2014))
    new_id = await library.create(an_item("2", "Тезис", year=2010))
    old_id = await library.create(an_item("3", "Тезис", year=2001))
    await wishlist.add(middle_id, now=MOMENT - timedelta(days=2))
    await wishlist.add(new_id, now=MOMENT)
    await wishlist.add(old_id, now=MOMENT - timedelta(days=5))

    found = await sections.ids(
        replace(WANTED, order=Order(Sort.TITLE, descending=False)),
        limit=50, offset=0,
    )

    assert found == [new_id, middle_id, old_id]


async def test_the_rated_section_breaks_ties_by_its_own_date(
    sessions, library, sections
):
    """Дата привязана к разделу, а не просто взята из двух подходящих колонок.

    Отложены здесь все трое, и закладки расставлены против оценок: возьми
    «Оценённые» чужую колонку — порядок выйдет обратным ожидаемому, а не
    случайным. Без этого подмена одной таблицы на другую прошла бы молча:
    оценки в тесте выше все равны, а закладок там нет вовсе."""
    ratings = RatingsRepository(sessions)
    wishlist = WishlistRepository(sessions)
    middle_id = await library.create(an_item("1", "На днях", year=2014))
    new_id = await library.create(an_item("2", "Только что", year=2010))
    old_id = await library.create(an_item("3", "Давно", year=2001))
    for item_id, rated_days, wished_days in [(middle_id, 2, 0), (new_id, 0, 5),
                                             (old_id, 5, 2)]:
        await ratings.set_score(item_id, 8.0,
                                now=MOMENT - timedelta(days=rated_days))
        await wishlist.add(item_id, now=MOMENT - timedelta(days=wished_days))

    found = await sections.ids(RATED, limit=50, offset=0)

    assert found == [new_id, middle_id, old_id]


async def test_the_other_side_of_the_order(sessions, library, sections):
    """Кнопка в шапке перебирает четыре критерия в две стороны."""
    ratings = RatingsRepository(sessions)
    middle_id = await library.create(an_item("1", "Средне", year=2014))
    high_id = await library.create(an_item("2", "Отлично", year=2010))
    low_id = await library.create(an_item("3", "Так себе", year=2001))
    await ratings.set_score(middle_id, 8.0, now=MOMENT)
    await ratings.set_score(high_id, 10.0, now=MOMENT)
    await ratings.set_score(low_id, 5.0, now=MOMENT)

    found = await sections.ids(
        replace(RATED, order=Order(Sort.SCORE, descending=False)),
        limit=50, offset=0,
    )

    assert found == [low_id, middle_id, high_id]


async def test_the_alphabet_ignores_case(sessions, library, sections):
    """Встроенный в SQLite lower() умеет только ASCII: без py_lower порядок
    получается побайтовый, и заглавная «Я» встаёт впереди строчной «а».

    Набор подобран под это: у «Яблоко», «Аватар» и «автобус» побайтовый порядок
    и алфавитный расходятся. Со строчным «яблоко» они совпадали бы, и потеря
    приведения прошла бы молча."""
    ratings = RatingsRepository(sessions)
    ids = {}
    for source_id, title in [("1", "Яблоко"), ("2", "Аватар"), ("3", "автобус")]:
        item_id = await library.create(an_item(source_id, title, year=2014))
        await ratings.set_score(item_id, 8.0, now=MOMENT)
        ids[title] = item_id

    found = await sections.ids(
        replace(RATED, order=Order(Sort.TITLE, descending=False)),
        limit=50, offset=0,
    )

    assert found == [ids["Аватар"], ids["автобус"], ids["Яблоко"]]
