"""Отбор ленты фильтрами: включённые, исключённые и их сочетания.

Отдельно от `test_sections.py`: тот про то, что раздел показывает и в каком
порядке, а этот — про то, чем набор сужают. Общего у них ровно запрос, и он
проверяется порознь: сортировка от фильтра не зависит вовсе."""

from dataclasses import replace

import pytest

from backend.model import Filters, Kind
from backend.storage.repository.genres import GenresRepository
from backend.storage.repository.library import LibraryRepository
from backend.storage.repository.ratings import RatingsRepository
from backend.storage.repository.tags import TagsRepository
from backend.storage.repository.wishlist import WishlistRepository
from tests.conftest import ACTION, ADVENTURE, DRAMA, MOMENT, RATED, WANTED, an_item


@pytest.fixture
async def library(sessions):
    return LibraryRepository(sessions)


async def test_a_tag_filter_narrows_the_section(sessions, library, sections):
    ratings = RatingsRepository(sessions)
    tags = TagsRepository(sessions)
    tagged_id = await library.create(an_item("1", "С меткой", year=2014))
    other_id = await library.create(an_item("2", "Без метки", year=2010))
    for item_id in (tagged_id, other_id):
        await ratings.set_score(item_id, 8.0, now=MOMENT)
    tag_id = await tags.create(Kind.MOVIE, "пересмотреть")
    await tags.assign(tagged_id, tag_id)

    found = await sections.ids(
        replace(RATED, filters=Filters(tag_ids=(tag_id,))), limit=50, offset=0
    )

    assert found == [tagged_id]


async def test_two_tags_are_joined_by_and(sessions, library, sections):
    """Решение пользователя 02.08.2026: каждая добавленная метка сужает набор,
    а не расширяет его. Раньше здесь было «или», и вторая метка приводила
    карточки, которых с первой не было."""
    ratings = RatingsRepository(sessions)
    tags = TagsRepository(sessions)
    both_id = await library.create(an_item("1", "С обеими", year=2014))
    one_id = await library.create(an_item("2", "С одной", year=2010))
    for item_id in (both_id, one_id):
        await ratings.set_score(item_id, 8.0, now=MOMENT)
    first_tag = await tags.create(Kind.MOVIE, "пересмотреть")
    second_tag = await tags.create(Kind.MOVIE, "с женой")
    stranger = await tags.create(Kind.MOVIE, "не выбирали")
    await tags.assign(both_id, first_tag)
    await tags.assign(both_id, second_tag)
    # Меток у второй карточки тоже две, и вторая не выбрана: со счётом без
    # отбора по выбранным «две любых» и «две эти» неразличимы, и фильтр по паре
    # тегов привёл бы карточку с двумя чужими.
    await tags.assign(one_id, first_tag)
    await tags.assign(one_id, stranger)

    found = await sections.ids(
        replace(RATED, filters=Filters(tag_ids=(first_tag, second_tag))),
        limit=50, offset=0,
    )

    assert found == [both_id]


async def test_a_genre_filter_narrows_the_section(sessions, reference, library,
                                                  sections):
    ratings = RatingsRepository(sessions)
    genres = GenresRepository(sessions)
    drama_id = await library.create(an_item("1", "Драма", year=2014))
    other_id = await library.create(an_item("2", "Не драма", year=2010))
    for item_id in (drama_id, other_id):
        await ratings.set_score(item_id, 8.0, now=MOMENT)
    genre_ids = [DRAMA]
    await genres.set_for_item(drama_id, genre_ids)

    found = await sections.ids(
        replace(RATED, filters=Filters(genre_ids=tuple(genre_ids))),
        limit=50, offset=0,
    )

    assert found == [drama_id]


async def test_two_genres_are_joined_by_and(sessions, reference, library,
                                            sections):
    """Жанры сужают так же, как метки: выбрал боевик и приключения — получил то,
    что и то и другое разом.

    У одной карточки оба жанра, у другой только боевик: первая обязана пройти,
    вторая — нет."""
    ratings = RatingsRepository(sessions)
    genres = GenresRepository(sessions)
    both_id = await library.create(an_item("1", "Боевик и приключения"))
    one_id = await library.create(an_item("2", "Только боевик"))
    for item_id in (both_id, one_id):
        await ratings.set_score(item_id, 8.0, now=MOMENT)
    pair = [ACTION, ADVENTURE]
    await genres.set_for_item(both_id, pair)
    await genres.set_for_item(
        one_id, [ACTION])

    found = await sections.ids(
        replace(RATED, filters=Filters(genre_ids=tuple(pair))),
        limit=50, offset=0,
    )

    assert found == [both_id]


async def test_a_tag_and_a_genre_are_joined_by_and(sessions, reference, library,
                                                   sections):
    """И между признаками, и внутри признака — «и»."""
    ratings = RatingsRepository(sessions)
    genres = GenresRepository(sessions)
    tags = TagsRepository(sessions)
    both_id = await library.create(an_item("1", "И то и то", year=2014))
    only_tag_id = await library.create(an_item("2", "Только метка", year=2010))
    for item_id in (both_id, only_tag_id):
        await ratings.set_score(item_id, 8.0, now=MOMENT)

    genre_ids = [DRAMA]
    await genres.set_for_item(both_id, genre_ids)
    tag_id = await tags.create(Kind.MOVIE, "пересмотреть")
    await tags.assign(both_id, tag_id)
    await tags.assign(only_tag_id, tag_id)

    found = await sections.ids(
        replace(RATED, filters=Filters(tag_ids=(tag_id,),
                                       genre_ids=tuple(genre_ids))),
        limit=50, offset=0,
    )

    assert found == [both_id]


async def test_a_score_filter_takes_whole_columns(sessions, library, sections):
    """Фильтр по оценке говорит теми же столбцами, что и гистограмма, а те —
    теми же ступенями, что и карточка: 7.66 у игры — это столбец 8. Проба выше
    половины нарочно: на 7.33 округление вниз дало бы ту же семёрку."""
    ratings = RatingsRepository(sessions)
    eight_id = await library.create(an_item("1", "Восьмёрка", year=2014))
    nine_id = await library.create(an_item("2", "Девятка", year=2010))
    await ratings.set_score(eight_id, 7.66, now=MOMENT)
    await ratings.set_score(nine_id, 9.0, now=MOMENT)

    found = await sections.ids(
        replace(RATED, filters=Filters(scores=(8,))), limit=50, offset=0
    )

    assert found == [eight_id]


async def test_two_scores_stay_joined_by_or(sessions, library, sections):
    """Оценка — единственный признак, где «или» остаётся, и не по решению, а по
    устройству: она у карточки одна, и «семь и восемь разом» не бывает ни у
    чего. Переведи её на «и» — лента опустеет при любом выборе."""
    ratings = RatingsRepository(sessions)
    seven_id = await library.create(an_item("1", "Семёрка"))
    eight_id = await library.create(an_item("2", "Восьмёрка"))
    nine_id = await library.create(an_item("3", "Девятка"))
    for item_id, score in ((seven_id, 7.0), (eight_id, 8.0), (nine_id, 9.0)):
        await ratings.set_score(item_id, score, now=MOMENT)

    found = await sections.ids(
        replace(RATED, filters=Filters(scores=(7, 8))), limit=50, offset=0
    )

    assert sorted(found) == sorted([seven_id, eight_id])


async def test_an_excluded_tag_wins_over_an_included_genre(
    sessions, reference, library, sections
):
    """Исключённое вычитается последним и сильнее включённого: выбрал драму,
    исключил метку — карточка с обеими не покажется."""
    ratings = RatingsRepository(sessions)
    genres = GenresRepository(sessions)
    tags = TagsRepository(sessions)

    both_id = await library.create(an_item("1", "И драма, и метка", year=2014))
    only_genre_id = await library.create(an_item("2", "Только драма", year=2010))
    for item_id in (both_id, only_genre_id):
        await ratings.set_score(item_id, 8.0, now=MOMENT)
        await genres.set_for_item(item_id, [DRAMA])

    tag_id = await tags.create(Kind.MOVIE, "не хочу видеть")
    await tags.assign(both_id, tag_id)

    genre_ids = [DRAMA]
    found = await sections.ids(
        replace(RATED, filters=Filters(genre_ids=tuple(genre_ids),
                                       excluded_tag_ids=(tag_id,))),
        limit=50, offset=0,
    )

    assert found == [only_genre_id]


async def test_an_excluded_genre_removes_the_card(
    sessions, reference, library, sections
):
    ratings = RatingsRepository(sessions)
    genres = GenresRepository(sessions)
    drama_id = await library.create(an_item("1", "Драма", year=2014))
    plain_id = await library.create(an_item("2", "Без жанра", year=2010))
    for item_id in (drama_id, plain_id):
        await ratings.set_score(item_id, 8.0, now=MOMENT)

    genre_ids = [DRAMA]
    await genres.set_for_item(drama_id, genre_ids)

    found = await sections.ids(
        replace(RATED, filters=Filters(excluded_genre_ids=tuple(genre_ids))),
        limit=50, offset=0,
    )

    assert found == [plain_id]


async def test_two_excluded_mean_neither_of_them(sessions, library, sections):
    """Исключение осталось «ни одного из этих», а не «не все сразу»: карточка с
    одной из двух исключённых меток тоже уходит. На одной метке это неотличимо
    от включения, и подмена прошла бы молча."""
    ratings = RatingsRepository(sessions)
    tags = TagsRepository(sessions)
    one_id = await library.create(an_item("1", "С одной из"))
    clean_id = await library.create(an_item("2", "Ни с одной"))
    for item_id in (one_id, clean_id):
        await ratings.set_score(item_id, 8.0, now=MOMENT)
    first_tag = await tags.create(Kind.MOVIE, "скучное")
    second_tag = await tags.create(Kind.MOVIE, "не досмотрел")
    await tags.assign(one_id, first_tag)

    found = await sections.ids(
        replace(RATED,
                filters=Filters(excluded_tag_ids=(first_tag, second_tag))),
        limit=50, offset=0,
    )

    assert found == [clean_id]


async def test_an_excluded_score_removes_the_column(sessions, library, sections):
    """Оценка дробная, как у игры: исключается столбец, а не число. С ровной
    семёркой округление в этой ветке можно было бы потерять незаметно, а с
    оценкой ниже половины — потерять его направление."""
    ratings = RatingsRepository(sessions)
    eight_id = await library.create(an_item("1", "Восьмёрка", year=2014))
    nine_id = await library.create(an_item("2", "Девятка", year=2010))
    await ratings.set_score(eight_id, 7.66, now=MOMENT)
    await ratings.set_score(nine_id, 9.0, now=MOMENT)

    found = await sections.ids(
        replace(RATED, filters=Filters(excluded_scores=(8,))),
        limit=50, offset=0,
    )

    assert found == [nine_id]


async def test_an_excluded_score_does_not_empty_the_wishlist(
    sessions, library, sections
):
    """У отложенного, но не оценённого, score пуст, а `NULL NOT IN (7)` в SQL
    — это NULL, а не истина. Без защиты от NULL исключение по оценке выносит из
    раздела «Хочу посмотреть» вообще всё, и молча."""
    item_id = await library.create(an_item("1", "Отложенный", year=2014))
    await WishlistRepository(sessions).add(item_id, now=MOMENT)

    found = await sections.ids(
        replace(WANTED, filters=Filters(excluded_scores=(7,))),
        limit=50, offset=0,
    )

    assert found == [item_id]


async def test_nothing_included_changes_nothing(sessions, library, sections):
    """Пустой фильтр не должен превращаться в `IN ()`: такое условие в SQL ложно
    для всех строк, и лента опустела бы. Охраняют это `if` в `_included`.

    С исключениями наоборот, и потому они здесь не проверяются: `NOT IN ()`
    истинно для всех строк, так что снятие охраняющих `if` в `_excluded`
    наблюдаемого поведения не меняет вовсе."""
    ratings = RatingsRepository(sessions)
    item_id = await library.create(an_item("1", "Оценённый", year=2014))
    await ratings.set_score(item_id, 8.0, now=MOMENT)

    found = await sections.ids(RATED, limit=50, offset=0)

    assert found == [item_id]
