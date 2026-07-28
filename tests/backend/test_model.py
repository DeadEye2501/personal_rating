from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from backend.model import Item, Kind, Rating, Source, average_score


def test_average_of_three_aspects_is_not_rounded():
    # Спека называет 7.33 как законное значение: округление живёт в показе.
    assert average_score(8, 7, 7) == pytest.approx(7.3333, abs=1e-4)


def test_empty_aspects_do_not_drag_the_average_down():
    assert average_score(8, None, 6) == 7.0


def test_single_aspect_is_its_own_average():
    assert average_score(None, 9, None) == 9.0


def test_no_aspects_at_all_gives_nothing():
    assert average_score(None, None, None) is None


def test_zero_is_a_value_and_not_an_absence():
    assert average_score(0, 10, None) == 5.0


def test_item_is_frozen():
    item = Item(
        id=1,
        kind=Kind.MOVIE,
        source=Source.TMDB,
        source_id="157336",
        title="Интерстеллар",
        synced_at=datetime(2026, 7, 27),
    )
    with pytest.raises(FrozenInstanceError):
        item.title = "другое"


def test_optional_fields_have_sane_defaults():
    item = Item(
        id=1,
        kind=Kind.GAME,
        source=Source.STEAM,
        source_id="292030",
        title="The Witcher 3",
        synced_at=datetime(2026, 7, 27),
    )
    assert item.year is None
    assert item.original_title == ""
    assert item.seasons_count is None


def test_rating_of_a_film_carries_no_aspects():
    rating = Rating(item_id=1, score=8.0)
    assert (rating.visual, rating.narrative, rating.gameplay) == (None, None, None)


def test_enum_values_match_the_schema():
    # Значения ложатся в базу текстом — они часть схемы, а не деталь кода.
    assert Kind.SERIES == "series"
    assert Source.MANUAL == "manual"
