"""Оценки агрегаторов: три состояния и сроки годности."""

from datetime import timedelta

from backend.model import ExternalRating, RatingSource
from backend.storage.repository.external import (
    EMPTY_TTL,
    VALUE_TTL,
    ExternalRatingsRepository,
)
from backend.storage.repository.library import LibraryRepository
from tests.conftest import MOMENT

WANTED = [RatingSource.IMDB, RatingSource.ROTTEN, RatingSource.KINOPOISK]


async def test_three_states_are_told_apart(sessions, card):
    item_id = await card()
    repository = ExternalRatingsRepository(sessions)

    await repository.record(
        item_id, ExternalRating(RatingSource.ROTTEN, None, MOMENT)
    )
    await repository.record(item_id, ExternalRating(RatingSource.IMDB, 8.6, MOMENT))
    # Про Кинопоиск не спрашивали вовсе — строки нет.

    # Списком, а не словарём: у `ratings_of` объявлен порядок по
    # источнику, а записаны они здесь в обратном алфавиту.
    assert await repository.ratings_of(item_id) == [
        ExternalRating(RatingSource.IMDB, 8.6, MOMENT),
        ExternalRating(RatingSource.ROTTEN, None, MOMENT),
    ]


async def test_an_empty_answer_is_not_a_missing_row(sessions, card):
    """Иначе фильм, которого MDBList не знает, перезапрашивался бы при
    каждом показе — так и было у предшественника."""
    item_id = await card()
    repository = ExternalRatingsRepository(sessions)
    await repository.record(
        item_id, ExternalRating(RatingSource.ROTTEN, None, MOMENT)
    )

    assert RatingSource.ROTTEN not in await repository.stale_sources(
        item_id, WANTED, now=MOMENT
    )


async def test_a_source_never_asked_is_stale(sessions, card):
    item_id = await card()
    repository = ExternalRatingsRepository(sessions)

    assert set(await repository.stale_sources(item_id, WANTED, now=MOMENT)) == set(
        WANTED
    )


async def test_a_value_lives_a_month(sessions, card):
    """Дни литералами, а не через `VALUE_TTL`: иначе тест сторожил бы
    механику протухания, а срок из его имени сдвинули бы молча."""
    item_id = await card()
    repository = ExternalRatingsRepository(sessions)
    await repository.record(item_id, ExternalRating(RatingSource.IMDB, 8.6, MOMENT))

    fresh = await repository.stale_sources(
        item_id, WANTED, now=MOMENT + timedelta(days=29)
    )
    expired = await repository.stale_sources(
        item_id, WANTED, now=MOMENT + timedelta(days=31)
    )

    assert RatingSource.IMDB not in fresh
    assert RatingSource.IMDB in expired


async def test_exactly_at_the_deadline_is_still_fresh(sessions, card):
    """Сравнение строгое: ровно в срок ещё не протухло."""
    item_id = await card()
    repository = ExternalRatingsRepository(sessions)
    await repository.record(item_id, ExternalRating(RatingSource.IMDB, 8.6, MOMENT))

    assert RatingSource.IMDB not in await repository.stale_sources(
        item_id, WANTED, now=MOMENT + VALUE_TTL
    )


async def test_an_empty_answer_lives_a_week(sessions, card):
    """У свежего релиза оценка ещё может появиться — но ходить за ней
    ежедневно незачем. Дни литералами, по тому же доводу."""
    item_id = await card()
    repository = ExternalRatingsRepository(sessions)
    await repository.record(
        item_id, ExternalRating(RatingSource.ROTTEN, None, MOMENT)
    )

    fresh = await repository.stale_sources(
        item_id, WANTED, now=MOMENT + timedelta(days=6)
    )
    expired = await repository.stale_sources(
        item_id, WANTED, now=MOMENT + timedelta(days=8)
    )

    assert RatingSource.ROTTEN not in fresh
    assert RatingSource.ROTTEN in expired


async def test_a_zero_is_a_value_and_lives_a_month(sessions, card):
    """Ноль — это оценка, а не пустой ответ. Отличать их надо по наличию строки,
    а не по правдивости числа: у Rotten Tomatoes нулевой рейтинг бывает, и по
    короткому сроку он перезапрашивался бы вчетверо чаще нужного."""
    item_id = await card()
    repository = ExternalRatingsRepository(sessions)
    await repository.record(item_id, ExternalRating(RatingSource.ROTTEN, 0.0, MOMENT))

    stale = await repository.stale_sources(
        item_id, WANTED, now=MOMENT + timedelta(days=8)
    )

    assert RatingSource.ROTTEN not in stale


async def test_the_empty_answer_expires_sooner_than_a_value(sessions, card):
    """Проверяются не константы, а поведение: в один и тот же момент пустой
    ответ уже протух, а значение рядом с ним ещё нет."""
    item_id = await card()
    repository = ExternalRatingsRepository(sessions)
    await repository.record(item_id, ExternalRating(RatingSource.IMDB, 8.6, MOMENT))
    await repository.record(
        item_id, ExternalRating(RatingSource.ROTTEN, None, MOMENT)
    )

    stale = await repository.stale_sources(
        item_id, WANTED, now=MOMENT + EMPTY_TTL + timedelta(days=1)
    )

    assert RatingSource.ROTTEN in stale
    assert RatingSource.IMDB not in stale


async def test_recording_again_moves_the_deadline(sessions, card):
    item_id = await card()
    repository = ExternalRatingsRepository(sessions)
    await repository.record(item_id, ExternalRating(RatingSource.IMDB, 8.6, MOMENT))

    later = MOMENT + VALUE_TTL + timedelta(days=1)
    await repository.record(item_id, ExternalRating(RatingSource.IMDB, 8.7, later))

    stored = {r.source: r.value for r in await repository.ratings_of(item_id)}
    assert stored[RatingSource.IMDB] == 8.7
    assert RatingSource.IMDB not in await repository.stale_sources(
        item_id, WANTED, now=later
    )


async def test_an_empty_answer_may_later_become_a_value(sessions, card):
    item_id = await card()
    repository = ExternalRatingsRepository(sessions)
    await repository.record(
        item_id, ExternalRating(RatingSource.ROTTEN, None, MOMENT)
    )

    later = MOMENT + EMPTY_TTL + timedelta(days=1)
    await repository.record(
        item_id, ExternalRating(RatingSource.ROTTEN, 72.0, later)
    )

    stored = {r.source: r.value for r in await repository.ratings_of(item_id)}
    assert stored[RatingSource.ROTTEN] == 72.0

    # И обратно: источник знал оценку, а теперь не отдаёт. `NULL` поверх
    # числа у upsert — отдельное поведение, и оно тоже наше.
    await repository.record(
        item_id, ExternalRating(RatingSource.ROTTEN, None, later)
    )
    assert await repository.ratings_of(item_id) == [
        ExternalRating(RatingSource.ROTTEN, None, later)
    ]


async def test_only_the_wanted_sources_are_reported(sessions, card):
    """У кино и у игр наборы источников разные, и запрошенный набор —
    фильтр: записанное вне него в ответ не доливается, даже протухшее."""
    item_id = await card()
    repository = ExternalRatingsRepository(sessions)
    await repository.record(item_id, ExternalRating(RatingSource.IMDB, 8.6, MOMENT))

    stale = await repository.stale_sources(
        item_id, [RatingSource.STEAM], now=MOMENT + timedelta(days=365)
    )
    assert stale == [RatingSource.STEAM]


async def test_ratings_of_one_card_do_not_leak_into_another(sessions, card):
    first = await card(source_id="1")
    second = await card(source_id="2")
    repository = ExternalRatingsRepository(sessions)
    await repository.record(first, ExternalRating(RatingSource.IMDB, 8.6, MOMENT))

    assert await repository.ratings_of(second) == []
    assert await repository.stale_sources(second, WANTED, now=MOMENT) == WANTED


async def test_ratings_go_away_with_the_card(sessions, card, posters):
    item_id = await card()
    repository = ExternalRatingsRepository(sessions)
    await repository.record(item_id, ExternalRating(RatingSource.IMDB, 8.6, MOMENT))

    await LibraryRepository(sessions).delete(item_id)

    assert await repository.ratings_of(item_id) == []
