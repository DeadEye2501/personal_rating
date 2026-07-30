"""Шесть клиентов источников, поднятых из настроек."""

import httpx

from backend.config import Config
from backend.sources.gog.client import GogClient
from backend.sources.http import SourceHttp
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
        one = SourceHttp(name, transport=transport)
        raised.append(one)
        return one

    kinopoisk = KinopoiskClient(
        PoiskkinoClient(http("kinopoisk"), config.poiskkino_key),
        UnofficialClient(http("kinopoisk"), config.kinopoisk_unofficial_key),
    )
    return Sources(
        tmdb=TmdbClient(http("tmdb"), config.tmdb_key),
        steam=SteamClient(http("steam")),
        gog=GogClient(http("gog")),
        mdblist=MdbListClient(http("mdblist"), config.mdblist_key),
        omdb=OmdbClient(http("omdb"), config.omdb_key),
        kinopoisk=kinopoisk,
        connections=tuple(raised),
    )
