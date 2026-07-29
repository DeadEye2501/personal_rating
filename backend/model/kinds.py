"""Закрытые наборы значений, которыми описывается карточка."""

from enum import StrEnum


class Kind(StrEnum):
    MOVIE = "movie"
    SERIES = "series"
    GAME = "game"


class Source(StrEnum):
    """Откуда пришла карточка. Владеет её идентичностью."""

    MANUAL = "manual"
    TMDB = "tmdb"
    STEAM = "steam"
    GOG = "gog"


class GenreSource(StrEnum):
    """Чей справочник жанров. Магазин даёт два: жанр и тег нумеруются у него
    порознь, и у Steam `9` — это жанр «Гонки» и тег «Стратегия» одновременно.
    Слитые в один источник, они выдали бы стратегии гонки."""

    TMDB = "tmdb"
    STEAM = "steam"
    STEAM_TAG = "steam_tag"
    GOG = "gog"
    GOG_TAG = "gog_tag"


class IdSource(StrEnum):
    """Всё, что не основной источник карточки."""

    IMDB = "imdb"
    KINOPOISK = "kinopoisk"
    STEAM = "steam"
    GOG = "gog"


class RatingSource(StrEnum):
    """Владелец оценки, а не тот, кто её привёз: Metascore из Steam — это
    metacritic, а доля положительных отзывов — steam."""

    IMDB = "imdb"
    KINOPOISK = "kinopoisk"
    TMDB = "tmdb"
    ROTTEN = "rotten"
    METACRITIC = "metacritic"
    STEAM = "steam"
    GOG = "gog"


class PersonRole(StrEnum):
    DIRECTOR = "director"
    ACTOR = "actor"
    SHOWRUNNER = "showrunner"


class CompanyRole(StrEnum):
    DEVELOPER = "developer"
    PUBLISHER = "publisher"


class GenreKind(StrEnum):
    """Наборов жанров два: кино и игры."""

    FILM = "film"
    GAME = "game"
