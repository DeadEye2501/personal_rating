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


class GenreSource(StrEnum):
    """Чей справочник жанров. По одному на источник: жанры и теги магазина —
    одно пространство меток, и приводит их к общему написанию сам источник."""

    TMDB = "tmdb"
    STEAM = "steam"
    GOG = "gog"
    OLD_GAMES = "old_games"


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
    """Наборов жанров четыре, и два из них пусты до второго этапа: списки для
    книг и музыки приедут из внешней базы вместе с клиентами под неё. Пустой
    набор — штатное состояние, а не заглушка: `list_for_kind` честно отдаёт
    пустой список, и фильтр жанров у этих двух типов пуст."""

    FILM = "film"
    GAME = "game"
    BOOK = "book"
    MUSIC = "music"
