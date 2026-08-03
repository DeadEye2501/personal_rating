"""Кто отвечает за какой тип содержимого.

Сборка живёт отдельно, в `sources/build.py`: растут эти две половины от разных
причин — маршрутизация от новых типов содержимого, сборка от новых источников."""

from dataclasses import dataclass

from backend.model import Kind, Source
from backend.sources.gog.client import GogClient
from backend.sources.http import SourceHttp
from backend.sources.oldgames.client import OldGamesClient
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
    oldgames: OldGamesClient
    mdblist: MdbListClient
    omdb: OmdbClient
    kinopoisk: KinopoiskClient
    connections: tuple[SourceHttp, ...]

    def catalog_for(self, kind: Kind) -> list:
        """У игр три равноправных источника, и покрытие даёт их сумма, а не
        каждый по отдельности: Steam и GOG — витрины и знают только то, что
        продаётся сегодня, old-games.ru закрывает ретро. «Дюны» нет ни в одной
        из витрин вовсе.

        Одну игру из двух-трёх источников склеивает `service/merging.py` — то,
        что склеивается без единой ошибки. Что не склеилось, остаётся на глазах
        человека: он убирает лишнее сам."""
        if kind is Kind.GAME:
            return [self.steam, self.gog, self.oldgames]
        return [self.tmdb]

    def people_for(self, kind: Kind) -> TmdbClient | None:
        """Кто умеет искать по человеку. У игр — никто, и это замерено, а не
        предположено: Steam по разработчику отдаёт разметку витрины, GOG молча
        игнорирует параметр и возвращает весь каталог. Людей же магазины не
        отдают вовсе, только компании."""
        return None if kind is Kind.GAME else self.tmdb

    def client_for(self, source: Source):
        """Каталожный клиент по источнику карточки. У ручной карточки его нет и
        быть не может: она ниоткуда не приезжает."""
        return {
            Source.TMDB: self.tmdb,
            Source.STEAM: self.steam,
            Source.GOG: self.gog,
            Source.OLD_GAMES: self.oldgames,
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
