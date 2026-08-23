"""Восемь клиентов источников, поднятых из настроек."""

import httpx

from backend.config import Config
from backend.model import Source
from backend.sources.gog.client import GogClient
from backend.sources.google_books.client import GoogleBooksClient
from backend.sources.http import SourceHttp
from backend.sources.oldgames.client import OldGamesClient
from backend.sources.ratings.kinopoisk.client import KinopoiskClient
from backend.sources.ratings.kinopoisk.poiskkino import PoiskkinoClient
from backend.sources.ratings.kinopoisk.unofficial import UnofficialClient
from backend.sources.ratings.mdblist.client import MdbListClient
from backend.sources.ratings.omdb.client import OmdbClient
from backend.sources.registry import Sources
from backend.sources.steam.client import SteamClient
from backend.sources.tmdb.client import TmdbClient


def build_sources(
    config: Config, transport: httpx.AsyncBaseTransport | None = None
) -> Sources:
    """Транспорт внедряется ради тестов: без него каждый клиент поднимает
    настоящий `AsyncClient` со своим SSL-контекстом."""
    raised: list[SourceHttp] = []

    def http(name: str) -> SourceHttp:
        # Свой предохранитель на источник: исчерпанная квота одного не должна
        # выключать остальных. Оба зеркала Кинопоиска при этом заводятся под
        # одним именем — наружу источник один.
        #
        # Каталожные зовутся значением `Source`, а не литералом: из того же
        # значения сборка собирает имя постерного соединения (`<источник>-poster`),
        # а по нему ищется предел одновременных запросов. С литералом
        # переименование источника уносило бы очередь у обложек и оставляло у
        # карточек, и не покраснело бы ничто.
        one = SourceHttp(str(name), transport=transport)
        raised.append(one)
        return one

    kinopoisk = KinopoiskClient(
        PoiskkinoClient(http("kinopoisk"), config.poiskkino_key),
        UnofficialClient(http("kinopoisk"), config.kinopoisk_unofficial_key),
    )
    return Sources(
        tmdb=TmdbClient(http(Source.TMDB), config.tmdb_key),
        steam=SteamClient(http(Source.STEAM)),
        gog=GogClient(http(Source.GOG)),
        old_games=OldGamesClient(http(Source.OLD_GAMES)),
        google_books=GoogleBooksClient(http(Source.GOOGLE_BOOKS),
                                       config.google_books_key),
        mdblist=MdbListClient(http("mdblist"), config.mdblist_key),
        omdb=OmdbClient(http("omdb"), config.omdb_key),
        kinopoisk=kinopoisk,
        connections=tuple(raised),
    )
