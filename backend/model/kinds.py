"""Закрытые наборы значений, которыми описывается карточка."""

from enum import StrEnum


class Kind(StrEnum):
    MOVIE = "movie"
    SERIES = "series"
    GAME = "game"
    BOOK = "book"
    MUSIC = "music"


class Source(StrEnum):
    """Откуда пришла карточка. Владеет её идентичностью."""

    MANUAL = "manual"
    TMDB = "tmdb"
    STEAM = "steam"
    GOG = "gog"
    OLD_GAMES = "old_games"
    GOOGLE_BOOKS = "google_books"


class GenreSource(StrEnum):
    """Чей справочник жанров. По одному на источник: жанры и теги магазина —
    одно пространство меток, и приводит их к общему написанию сам источник."""

    TMDB = "tmdb"
    STEAM = "steam"
    GOG = "gog"
    OLD_GAMES = "old_games"
    GOOGLE_BOOKS = "google_books"
    DEEZER = "deezer"


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
    AUTHOR = "author"
    PERFORMER = "performer"


class CompanyRole(StrEnum):
    DEVELOPER = "developer"
    PUBLISHER = "publisher"


class GenreKind(StrEnum):
    """Наборов жанров четыре: кино, игры, книги и музыка.

    Книжный и музыкальный заведены ревизией `0003` — 22 русских имени из BISAC,
    который отдаёт Google Books, и 21 английское, взятое у Deezer как есть."""

    FILM = "film"
    GAME = "game"
    BOOK = "book"
    MUSIC = "music"
