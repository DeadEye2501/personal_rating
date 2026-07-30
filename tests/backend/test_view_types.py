"""Карточка для показа: сборка из кандидата и из строки базы."""

from dataclasses import FrozenInstanceError
from datetime import date, datetime

import pytest

from backend.model import (
    CardView,
    Genre,
    GenreKind,
    GenreSource,
    ExternalRating,
    Item,
    Kind,
    RatingSource,
    Source,
    view_from_hit,
    view_from_item,
)
from tests.conftest import MOMENT, hit

DRAMA = Genre(id=1, name="Драма", kind=GenreKind.FILM)


def test_a_candidate_has_no_identifier_in_the_base():
    """Кандидат в выдаче — ещё не карточка: строки в базе нет."""
    view = view_from_hit(hit())
    assert view.item_id is None


def test_a_candidate_carries_what_the_search_gave():
    view = view_from_hit(hit(original_title="Interstellar", year=2014,
                             synopsis="про кукурузу",
                             poster_url="https://example.com/p.jpg"))
    assert (view.title, view.original_title, view.year, view.synopsis) == (
        "Интерстеллар", "Interstellar", 2014, "про кукурузу"
    )
    assert view.poster_url == "https://example.com/p.jpg"


def test_a_candidate_keeps_the_identity_it_was_found_by():
    """По этим трём его потом и загружают: тип решает, у кого спрашивать
    карточку, а пара источник—номер и есть адрес запроса."""
    view = view_from_hit(hit(kind=Kind.GAME, source=Source.STEAM,
                             source_id="292030"))
    assert (view.kind, view.source, view.source_id) == (
        Kind.GAME, Source.STEAM, "292030"
    )


def test_rows_the_search_does_not_fill_are_empty():
    """Ни длительности, ни состава в ответе поиска нет."""
    view = view_from_hit(hit())
    assert view.runtime is None
    assert view.people == ()
    assert view.rating is None
    assert view.in_wishlist is False


def test_genres_are_given_from_outside():
    """В выдаче приходят голые идентификаторы; разворачивает их справочник."""
    view = view_from_hit(hit(genre_ext_ids=((GenreSource.TMDB, "18"),)),
                         genres=(DRAMA,))
    assert view.genres == (DRAMA,)


def test_the_external_ratings_are_carried_through_as_given():
    """Кандидат несёт оценку, а собирает её тот, кто знает источники: таблица
    «у кого она приезжает даром» — знание об источниках, и живёт она в
    `sources/convert.py`, где её и проверяют."""
    given = (ExternalRating(RatingSource.TMDB, 8.4, MOMENT),)

    view = view_from_hit(hit(source_rating=8.4), external=given)

    assert view.external == given


def test_a_candidate_without_a_rating_has_none():
    """Пустая строка external_rating означает «спрашивали, у источника нет».
    Кандидата никто не спрашивал — фабриковать этот ответ нельзя."""
    assert view_from_hit(hit()).external == ()


def test_a_view_is_frozen():
    view = view_from_hit(hit())
    with pytest.raises(FrozenInstanceError):
        view.title = "другое"


def test_a_view_of_an_item_carries_every_field():
    """Тринадцать полей копируются вручную, и потеря любого тихая: карточка
    просто покажет пустую строку. Сверяем все."""
    item = Item(
        id=42, kind=Kind.SERIES, source=Source.TMDB, source_id="83867",
        title="Андор", synced_at=datetime(2026, 7, 27),
        original_title="Andor", year=2022, released_at=date(2022, 9, 21),
        synopsis="про восстание", poster_url="https://example.com/p.jpg",
        runtime=48, seasons_count=2, episodes_count=24,
    )

    view = view_from_item(item)

    assert view == CardView(
        item_id=42, kind=Kind.SERIES, source=Source.TMDB, source_id="83867",
        title="Андор", original_title="Andor", year=2022,
        synopsis="про восстание", poster_url="https://example.com/p.jpg",
        runtime=48, seasons_count=2, episodes_count=24,
        synced_at=datetime(2026, 7, 27),
    )
