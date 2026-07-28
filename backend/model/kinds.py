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
