"""Разбор вставленной ссылки на карточку источника."""

import pytest

from backend.model import Kind, Source
from backend.model.link import parse_link

ADDRESSES = [
    ("https://www.themoviedb.org/movie/157336",
     Source.TMDB, "157336", Kind.MOVIE),
    ("themoviedb.org/tv/83867", Source.TMDB, "83867", Kind.SERIES),
    ("https://store.steampowered.com/app/292030/",
     Source.STEAM, "292030", Kind.GAME),
    ("https://store.steampowered.com/app/292030/The_Witcher_3_Wild_Hunt/",
     Source.STEAM, "292030", Kind.GAME),
    ("https://www.gog.com/game/arcanum_of_steamworks_and_magick_obscura",
     Source.GOG, "arcanum_of_steamworks_and_magick_obscura", Kind.GAME),
    ("https://www.gog.com/en/game/arcanum", Source.GOG, "arcanum", Kind.GAME),
]


@pytest.mark.parametrize(("raw", "source", "source_id", "kind"), ADDRESSES)
def test_addresses_are_understood(raw, source, source_id, kind):
    link = parse_link(raw)
    assert (link.source, link.source_id, link.kind) == (source, source_id, kind)


def test_the_type_comes_from_the_path():
    """movie или tv в адресе — единственное, что отличает фильм от сериала."""
    assert parse_link("themoviedb.org/movie/1").kind is Kind.MOVIE
    assert parse_link("themoviedb.org/tv/1").kind is Kind.SERIES


def test_the_type_is_read_from_a_shouted_path_too():
    """Заглавные в слове пути образец пропускает, а таблица типов их не знает: без
    приведения к нижнему регистру разбор падал бы, а не отказывал."""
    assert parse_link("themoviedb.org/TV/1").kind is Kind.SERIES


def test_an_address_wins_over_the_toggle():
    """Стоишь на «Играх», вставил ссылку на фильм — верим ссылке."""
    link = parse_link("themoviedb.org/movie/157336", kind=Kind.GAME)
    assert (link.source, link.kind) == (Source.TMDB, Kind.MOVIE)


def test_a_game_address_wins_over_the_film_toggle():
    """И наоборот: тумблер на кино, а вставлена игра."""
    link = parse_link("https://store.steampowered.com/app/292030/",
                      kind=Kind.MOVIE)
    assert (link.source, link.kind) == (Source.STEAM, Kind.GAME)


def test_a_tail_after_the_identifier_is_dropped():
    link = parse_link("https://www.themoviedb.org/movie/157336-interstellar")
    assert link.source_id == "157336"


@pytest.mark.parametrize(("raw", "source_id"), [
    ("https://store.steampowered.com/app/292030/?snr=1_7_7_", "292030"),
    ("https://www.themoviedb.org/movie/157336?language=ru-RU", "157336"),
])
def test_query_parameters_are_dropped(raw, source_id):
    assert parse_link(raw).source_id == source_id


@pytest.mark.parametrize("kind", [Kind.MOVIE, Kind.SERIES])
def test_a_bare_identifier_is_accepted_for_films(kind):
    """У кино источник один, двусмысленности нет."""
    link = parse_link("157336", kind=kind)
    assert (link.source, link.source_id, link.kind) == (Source.TMDB, "157336", kind)


def test_a_bare_identifier_is_refused_for_games():
    """Steam и GOG нумеруются независимо: по числу их не различить."""
    assert parse_link("292030", kind=Kind.GAME) is None


def test_a_bare_identifier_without_a_type_is_refused():
    """Тип берётся из тумблера, и он всегда известен. Без него не гадаем."""
    assert parse_link("157336") is None


@pytest.mark.parametrize("raw", ["  themoviedb.org/movie/157336  ", "  157336  "])
def test_whitespace_is_trimmed(raw):
    """Копируют с пробелом на конце постоянно. Адрес нашёлся бы и без обрезки —
    его ищут внутри строки, — а голое число нет: у него проверяется вся строка
    целиком."""
    assert parse_link(raw, kind=Kind.MOVIE).source_id == "157336"


def test_the_age_gate_address_of_steam_is_understood():
    """У игр с возрастным шлюзом в строке браузера стоит именно этот адрес."""
    link = parse_link("https://store.steampowered.com/agecheck/app/292030/")
    assert (link.source, link.source_id) == (Source.STEAM, "292030")


SHOUTED = [
    ("https://www.GOG.com/game/arcanum", Source.GOG, "arcanum"),
    ("https://www.TheMovieDB.org/movie/157336", Source.TMDB, "157336"),
    ("https://Store.SteamPowered.com/app/292030/", Source.STEAM, "292030"),
    # Заглавные бывают не только в домене: слово пути и слаг приезжают такими же,
    # а слаг — это идентичность карточки, и с заглавными она была бы второй.
    ("https://www.themoviedb.org/Movie/157336", Source.TMDB, "157336"),
    ("https://www.gog.com/game/Arcanum", Source.GOG, "arcanum"),
]


@pytest.mark.parametrize(("raw", "source", "source_id"), SHOUTED)
def test_the_case_of_the_address_does_not_matter(raw, source, source_id):
    """Человек вставляет то, что скопировал: «GOG.com» из письма — обычное
    дело, и заглавные буквы бывают у всех трёх адресов."""
    link = parse_link(raw)
    assert (link.source, link.source_id) == (source, source_id)


NONSENSE = [
    "",
    "   ",
    "не ссылка",
    "https://example.com/",
    # Человек в базе есть, а карточки у него нет: страница не о вещи.
    "themoviedb.org/person/525",
    # Список, а не игра: `game` в пути обязателен.
    "https://www.gog.com/games?page=2",
    # Похожий домен, но чужой: разбор идёт по адресу, а не по слову в строке.
    "https://themoviedb.org.example.net/movie/157336",
    # Номер с хвостом голым не считается: проверяется вся строка, а не её начало.
    # Иначе в базу уехал бы идентификатор «157336-мусор» целиком.
    "157336-мусор",
    "157336 157337",
]


@pytest.mark.parametrize("raw", NONSENSE)
def test_nonsense_is_refused(raw):
    assert parse_link(raw, kind=Kind.MOVIE) is None
