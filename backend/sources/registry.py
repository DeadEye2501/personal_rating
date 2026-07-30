"""Кто отвечает за какой тип содержимого.

Сборка живёт отдельно, в `sources/build.py`: растут эти две половины от разных
причин — маршрутизация от новых типов содержимого, сборка от новых источников."""

from dataclasses import dataclass

from backend.model import Kind, Source
from backend.sources.gog.client import GogClient
from backend.sources.http import SourceHttp
from backend.sources.ratings.kinopoisk.client import KinopoiskClient
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

    async def aclose(self) -> None:
        for one in self.connections:
            await one.aclose()
