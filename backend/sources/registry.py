"""Кто отвечает за какой тип содержимого."""

from dataclasses import dataclass

import httpx

from backend.config import Config
from backend.model import Kind, Source
from backend.sources.gog.client import GogClient
from backend.sources.http import Breaker, SourceHttp
from backend.sources.ratings.kinopoisk.client import KinopoiskClient
from backend.sources.ratings.kinopoisk.poiskkino import PoiskkinoClient
from backend.sources.ratings.kinopoisk.unofficial import UnofficialClient
from backend.sources.ratings.mdblist.client import MdbListClient
from backend.sources.ratings.omdb.client import OmdbClient
from backend.sources.steam.client import SteamClient
from backend.sources.tmdb.client import TmdbClient


@dataclass(slots=True)
class Sources:
    """Поднятые клиенты и соединения под ними.

    Соединения перечислены здесь, а не собираются по клиентам: иначе реестру
    пришлось бы читать их приватное поле, а каждому клиенту — заводить пару
    свойств ради одного этого места."""

    tmdb: TmdbClient
    steam: SteamClient
    gog: GogClient
    mdblist: MdbListClient
    omdb: OmdbClient
    kinopoisk: KinopoiskClient
    connections: tuple[SourceHttp, ...]

    def catalog_for(self, kind: Kind) -> list:
        """У игр два равноправных магазина: заметная часть ретро в Steam не
        продаётся. Склейки в выдаче нет — решает человек."""
        if kind is Kind.GAME:
            return [self.steam, self.gog]
        return [self.tmdb]

    def client_for(self, source: Source):
        """Каталожный клиент по источнику карточки. У ручной карточки его нет и
        быть не может: она ниоткуда не приезжает."""
        return {
            Source.TMDB: self.tmdb,
            Source.STEAM: self.steam,
            Source.GOG: self.gog,
        }.get(source)

    def rating_sources(self, kind: Kind) -> list:
        """У игр оценки приходят вместе с карточкой — из Steam и GOG. Своего
        агрегатора им не нужно: ни ключа, ни запроса, ни квоты."""
        if kind is Kind.GAME:
            return []
        return [self.mdblist, self.omdb, self.kinopoisk]

    def breakers(self) -> list[Breaker]:
        return [one.breaker for one in self.connections]

    async def aclose(self) -> None:
        for one in self.connections:
            await one.aclose()


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
