"""Общее у разборов: перевод чужих кусков ответа в наши типы."""

import pytest

from backend.model import (
    CompanyRole,
    ExternalRating,
    GenreSource,
    RatingSource,
    Source,
)
from backend.sources.convert import (
    companies,
    from_search,
    genres,
    rating,
    year,
)
from tests.conftest import MOMENT


def test_the_developer_is_not_the_publisher():
    """У «Ведьмака» обе роли у одной студии, и на нём перестановка ролей
    незаметна. Здесь они разные: перепутав, карточка объявит издателя
    разработчиком, а человек этого уже не проверит."""
    payload = {"developers": ["Larian Studios"], "publishers": ["Bandai Namco"]}

    by_role = {one.role: one.name for one in companies(payload)}

    assert by_role == {
        CompanyRole.DEVELOPER: "Larian Studios",
        CompanyRole.PUBLISHER: "Bandai Namco",
    }


def test_a_studio_in_both_roles_appears_twice():
    """CD PROJEKT RED и разработчик, и издатель — это две разные строки, а не
    одна: роли в карточке показываются порознь."""
    payload = {"developers": ["CD PROJEKT RED"], "publishers": ["CD PROJEKT RED"]}

    assert len(companies(payload)) == 2


def test_a_response_without_studios_gives_none():
    assert companies({}) == ()


def test_studios_carry_no_identity():
    """Магазины отдают их голыми строками, и суррогат тут выдумывать нечего."""
    made = companies({"developers": ["Aspyr"]})

    assert made[0].source is None
    assert made[0].source_id is None


def test_the_space_travels_with_the_identifier():
    """`9` у Steam — это жанр «Гонки» и тег «Стратегия» одновременно. Номер без
    пространства справочник переведёт не в тот жанр."""
    marked = genres(GenreSource.STEAM_TAG, [{"id": 9}])

    assert marked == ((GenreSource.STEAM_TAG, "9"),)


def test_the_identifier_key_is_chosen_by_the_source():
    """У TMDB и Steam это число под `id`, у GOG — слаг под `slug`."""
    assert genres(GenreSource.GOG, [{"slug": "rpg"}], key="slug") == (
        (GenreSource.GOG, "rpg"),
    )


def test_a_genre_without_its_identifier_is_a_broken_answer():
    """Пропустив такой жанр молча, мы записали бы карточку с неполным набором
    и не узнали бы об этом никогда. Клиент ловит это и отвечает отказом."""
    with pytest.raises(KeyError):
        genres(GenreSource.TMDB, [{"name": "драма"}])


def test_the_year_starts_the_date():
    assert year("2014-11-05") == 2014
    assert year("2023.08.03") == 2023


def test_a_date_that_is_not_a_date_leaves_the_year_empty():
    assert year("") is None
    assert year(None) is None
    assert year("Coming soon") is None


def test_a_rating_keeps_the_owner_it_was_given():
    made = rating(RatingSource.METACRITIC, 93, MOMENT)

    assert [(one.source, one.value) for one in made] == [
        (RatingSource.METACRITIC, 93.0)
    ]
    assert made[0].fetched_at == MOMENT


def test_nothing_and_zero_are_both_an_absence_here():
    """Ноль у TMDB означает «никто не оценил», и записать его значило бы
    объявить, что фильм оценили в ноль. У Кинопоиска правило другое, и разбор
    там свой — общим этот случай не считается."""
    assert rating(RatingSource.TMDB, None, MOMENT) == ()
    assert rating(RatingSource.TMDB, 0, MOMENT) == ()


def test_the_free_rating_of_the_source_belongs_to_its_owner():
    """Оценка TMDB приходит в том же ответе поиска — она бесплатна, и владелец у
    неё тот, кто её отдал."""
    assert from_search(Source.TMDB, 8.4, MOMENT) == (
        ExternalRating(RatingSource.TMDB, 8.4, MOMENT),
    )
    assert from_search(Source.GOG, 4.5, MOMENT) == (
        ExternalRating(RatingSource.GOG, 4.5, MOMENT),
    )


def test_a_source_that_does_not_give_a_rating_in_search_brings_none():
    """У Steam в выдаче оценки нет вовсе, и строки быть не должно даже тогда,
    когда число в кандидате есть: оно означало бы не то."""
    assert from_search(Source.STEAM, 0.94, MOMENT) == ()


def test_a_free_rating_that_did_not_come_brings_none():
    assert from_search(Source.TMDB, None, MOMENT) == ()
