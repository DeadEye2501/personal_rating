"""Гистограмма своих оценок по отфильтрованному набору."""

import pytest

from backend.model import Filters, GenreSource, Kind, Source
from backend.storage.repository.genres import GenresRepository
from backend.storage.repository.tags import TagsRepository
from backend.storage.repository.wishlist import WishlistRepository
from tests.conftest import MOMENT, rated


async def columns(sections, kind: Kind = Kind.MOVIE, **filters) -> dict[int, int]:
    histogram = await sections.histogram(kind, Filters(**filters))
    return {bucket.score: bucket.count for bucket in histogram.buckets}


async def test_there_are_always_ten_columns(sessions, sections):
    """Пустой столбец — это сведение, а не отсутствие данных, поэтому на пустой
    библиотеке столбцов всё равно десять. Средней при этом нет вовсе: выдумывать
    ноль незачем, ноль — это оценка."""
    histogram = await sections.histogram(Kind.MOVIE, Filters())

    assert [b.score for b in histogram.buckets] == list(range(1, 11))
    assert all(b.count == 0 for b in histogram.buckets)
    assert (histogram.total, histogram.average) == (0, None)


async def test_a_score_lands_in_its_column(sessions, sections):
    await rated(sessions, "1", 8.0)

    buckets = await columns(sections)

    assert buckets[8] == 1
    assert buckets[7] == 0


async def test_a_fraction_is_rounded_down(sessions, sections):
    """У игр оценка — среднее трёх шкал, то есть 7.33: это столбец 7."""
    await rated(sessions, "292030", 7.33, kind=Kind.GAME, source=Source.STEAM)

    buckets = await columns(sections, Kind.GAME)

    assert (buckets[7], buckets[8]) == (1, 0)


async def test_a_ten_stays_a_ten(sessions, sections):
    """Верхняя граница — единственное место, где округление вниз могло бы
    выкинуть оценку за пределы шкалы."""
    await rated(sessions, "1", 10.0)

    assert (await columns(sections))[10] == 1


async def test_a_one_lands_in_the_first_column(sessions, sections):
    """Нижняя граница шкалы. Без единицы в наборе сдвиг начала диапазона
    столбцов заметить нечем: у остальных оценок свои столбцы есть."""
    await rated(sessions, "1", 1.0)

    assert (await columns(sections))[1] == 1


async def test_a_bookmarked_card_is_counted_by_its_score(sessions, sections):
    """Отложить оценённое можно — например, чтобы пересмотреть. Гистограмма
    считает по оценке и на закладку не смотрит вовсе."""
    item_id = await rated(sessions, "1", 8.0)
    await WishlistRepository(sessions).add(item_id, now=MOMENT)

    histogram = await sections.histogram(Kind.MOVIE, Filters())

    assert {b.score: b.count for b in histogram.buckets}[8] == 1
    assert histogram.total == 1


async def test_the_unrated_are_not_counted(sessions, sections):
    await rated(sessions, "1", None)

    histogram = await sections.histogram(Kind.MOVIE, Filters())
    assert sum(b.count for b in histogram.buckets) == 0
    assert histogram.total == 0


async def test_the_type_of_content_never_mixes(sessions, sections):
    await rated(sessions, "1", 8.0)
    await rated(sessions, "292030", 9.0, kind=Kind.GAME, source=Source.STEAM)

    buckets = await columns(sections)

    assert (buckets[8], buckets[9]) == (1, 0)


async def test_the_histogram_obeys_the_same_filters_as_the_feed(
    sessions, reference, sections
):
    """Ради этого гистограмма и стоит на общем запросе: иначе отфильтрованную
    гистограмму не увидеть никогда."""
    genres = GenresRepository(sessions)
    drama_id = await rated(sessions, "1", 8.0)
    await rated(sessions, "2", 9.0)
    genre_ids = await genres.resolve(GenreSource.TMDB, ["18"])
    await genres.set_for_item(drama_id, genre_ids)

    buckets = await columns(sections, genre_ids=tuple(genre_ids))

    assert (buckets[8], buckets[9]) == (1, 0)


async def test_the_histogram_does_not_filter_itself_by_score(sessions, sections):
    """Фильтр по оценке — это те же десять столбцов. Применив его к себе,
    гистограмма показала бы ровно то, что ты в ней и выбрал."""
    await rated(sessions, "1", 7.0)
    await rated(sessions, "2", 9.0)

    buckets = await columns(sections, scores=(7,))

    assert (buckets[7], buckets[9]) == (1, 1)


async def test_the_histogram_ignores_an_excluded_score_too(sessions, sections):
    """Снимается весь признак целиком, обе его стороны."""
    await rated(sessions, "1", 7.0)
    await rated(sessions, "2", 9.0)

    histogram = await sections.histogram(Kind.MOVIE,
                                         Filters(excluded_scores=(7,)))
    buckets = {b.score: b.count for b in histogram.buckets}

    assert (buckets[7], buckets[9]) == (1, 1)
    assert histogram.total == 2


async def test_a_tag_filter_still_narrows_the_histogram(sessions, sections):
    """Снимается только фильтр по оценке — прочие признаки гистограмма слушает."""
    tags = TagsRepository(sessions)
    tagged_id = await rated(sessions, "1", 7.0)
    await rated(sessions, "2", 9.0)
    tag_id = await tags.create(Kind.MOVIE, "пересмотреть")
    await tags.assign(tagged_id, tag_id)

    buckets = await columns(sections, tag_ids=(tag_id,), scores=(7,))

    assert (buckets[7], buckets[9]) == (1, 0)


async def test_an_excluded_tag_still_narrows_the_histogram(sessions, sections):
    """Снимается фильтр по оценке — и только он. Обе стороны прочих признаков
    гистограмма слушает, иначе исключение метки в ней бы не отражалось."""
    tags = TagsRepository(sessions)
    tagged_id = await rated(sessions, "1", 7.0)
    await rated(sessions, "2", 9.0)
    tag_id = await tags.create(Kind.MOVIE, "не хочу видеть")
    await tags.assign(tagged_id, tag_id)

    buckets = await columns(sections, excluded_tag_ids=(tag_id,), scores=(7,))

    assert (buckets[7], buckets[9]) == (0, 1)


async def test_several_cards_pile_up_in_one_column(sessions, sections):
    for number in range(3):
        await rated(sessions, str(number), 8.0)

    assert (await columns(sections))[8] == 3


async def test_the_footer_counts_everything_in_the_columns(sessions, sections):
    await rated(sessions, "1", 7.0)
    await rated(sessions, "2", 9.0)

    histogram = await sections.histogram(Kind.MOVIE, Filters())

    assert histogram.total == 2
    assert histogram.average == 8.0


async def test_the_average_is_not_collected_from_the_columns(sessions, sections):
    """У игр оценка — среднее трёх шкал. Собранная из округлённых вниз
    столбцов средняя занизила бы результат почти на полбалла."""
    for number, score in enumerate([7.33, 7.66, 8.0]):
        await rated(sessions, str(number), score, kind=Kind.GAME,
                   source=Source.STEAM)

    histogram = await sections.histogram(Kind.GAME, Filters())

    assert histogram.average == pytest.approx(7.6633, abs=1e-4)
    # По столбцам вышло бы (7 + 7 + 8) / 3 = 7.33.
    assert histogram.average > 7.5


async def test_the_footer_obeys_the_filters(sessions, reference, sections):
    genres = GenresRepository(sessions)
    drama_id = await rated(sessions, "1", 6.0)
    await rated(sessions, "2", 10.0)
    genre_ids = await genres.resolve(GenreSource.TMDB, ["18"])
    await genres.set_for_item(drama_id, genre_ids)

    histogram = await sections.histogram(Kind.MOVIE,
                                         Filters(genre_ids=tuple(genre_ids)))

    assert (histogram.total, histogram.average) == (1, 6.0)
