from dataclasses import FrozenInstanceError

import pytest

from backend.model import (
    CompanyRole,
    Credit,
    ExternalId,
    ExternalRating,
    Genre,
    GenreKind,
    GenreSource,
    IdSource,
    Item,
    Kind,
    PersonRole,
    Rating,
    RatingSource,
    Source,
    average_score,
)
from tests.conftest import MOMENT


def test_average_of_three_aspects_is_not_rounded():
    # Спека называет 7.33 как законное значение: округление живёт в показе.
    assert average_score(8, 7, 7) == pytest.approx(7.3333, abs=1e-4)


def test_empty_aspects_do_not_drag_the_average_down():
    assert average_score(8, None, 6) == 7.0


def test_single_aspect_is_its_own_average():
    assert average_score(None, 9, None) == 9.0


def test_no_aspects_at_all_gives_nothing():
    assert average_score(None, None, None) is None


def test_zero_counts_as_a_filled_aspect():
    # Шкала в спеке 1–10, нуля на ней нет — проверяется именно то, что функция
    # отличает выставленное от невыставленного по `is None`, а не по ложности.
    assert average_score(0, 10, None) == 5.0


FROZEN = [
    (Item(id=1, kind=Kind.MOVIE, source=Source.TMDB, source_id="157336",
          title="Интерстеллар", synced_at=MOMENT), "title", "другое"),
    (Rating(item_id=1, score=8.0), "score", 1.0),
    (Credit(name="Нолан", role=PersonRole.DIRECTOR), "name", "не Нолан"),
    (Genre(id=1, name="Драма", kind=GenreKind.FILM), "name", "Комедия"),
    (ExternalId(source=IdSource.IMDB, value="tt0816692"), "value", "tt0000000"),
    (ExternalRating(source=RatingSource.IMDB, value=8.6, fetched_at=MOMENT),
     "value", 1.0),
]


@pytest.mark.parametrize(("value", "field", "other"), FROZEN,
                         ids=lambda item: type(item).__name__)
def test_boundary_types_are_frozen(value, field, other):
    # Через границу слоёв они ходят между потоками: разморозь один — и
    # состояние карточки поедет вслед за ссылкой.
    with pytest.raises(FrozenInstanceError):
        setattr(value, field, other)


def test_optional_fields_have_sane_defaults():
    # Умолчания уезжают в базу как есть: строка вместо None у необязательного
    # поля — это пустое название вместо «неизвестно».
    item = Item(
        id=1,
        kind=Kind.GAME,
        source=Source.STEAM,
        source_id="292030",
        title="The Witcher 3",
        synced_at=MOMENT,
    )
    assert (item.original_title, item.synopsis, item.poster_url) == ("", "", "")
    assert (item.year, item.released_at, item.runtime) == (None, None, None)
    assert (item.seasons_count, item.episodes_count) == (None, None)


def test_rating_of_a_film_carries_no_aspects():
    rating = Rating(item_id=1, score=8.0)
    assert (rating.visual, rating.narrative, rating.gameplay) == (None, None, None)


# Значения ложатся в базу текстом — они часть схемы, а не деталь кода:
# переименование здесь ломает уже записанные строки, а не только код.
SCHEMA = [
    (Kind, {"movie", "series", "game"}),
    (Source, {"manual", "tmdb", "steam", "gog"}),
    (IdSource, {"imdb", "kinopoisk", "steam", "gog"}),
    (RatingSource, {"imdb", "kinopoisk", "tmdb", "rotten", "metacritic",
                    "steam", "gog"}),
    (PersonRole, {"director", "actor", "showrunner"}),
    (CompanyRole, {"developer", "publisher"}),
    (GenreKind, {"film", "game"}),
    (GenreSource, {"tmdb", "steam", "steam_tag", "gog", "gog_tag"}),
]


@pytest.mark.parametrize(("enum", "expected"), SCHEMA,
                         ids=lambda item: getattr(item, "__name__", ""))
def test_enum_values_match_the_schema(enum, expected):
    """Набор значений, а не привязка члена к значению: обмен двух членов местами
    здесь не виден, и ловят его те тесты, что читают сырую колонку, —
    `test_library.py` для `Kind` и `Source`, `test_credits.py` для ролей,
    `test_tmdb_card.py` для `IdSource`, фикстура справочника для `GenreSource`."""
    assert {member.value for member in enum} == expected
