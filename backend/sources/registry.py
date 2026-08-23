"""Кто отвечает за какой тип содержимого.

Сборка живёт отдельно, в `sources/build.py`: растут эти две половины от разных
причин — маршрутизация от новых типов содержимого, сборка от новых источников."""

from dataclasses import dataclass

from backend.model import Kind, Source
from backend.sources.deezer.client import DeezerClient
from backend.sources.fantlab.client import FantLabClient
from backend.sources.gog.client import GogClient
from backend.sources.google_books.client import GoogleBooksClient
from backend.sources.http import SourceHttp
from backend.sources.oldgames.client import OldGamesClient
from backend.sources.ratings.kinopoisk.client import KinopoiskClient
from backend.sources.ratings.mdblist.client import MdbListClient
from backend.sources.ratings.omdb.client import OmdbClient
from backend.sources.steam.client import SteamClient
from backend.sources.tmdb.client import TmdbClient


@dataclass(frozen=True, slots=True)
class Route:
    """Кто отвечает за один тип содержимого. Клиенты названы именами полей
    `Sources`, а не объектами: таблица объявляется до того, как хоть один клиент
    поднят, и читать её должны в том числе тесты границы — без сети и без
    ключей."""

    catalogs: tuple[str, ...]
    people: str | None
    ratings: tuple[str, ...]
    # Кто ищет обложку, когда у каталога её нет. Есть только у книг: замерено
    # 23.08.2026, у Google картинки нет у большинства бумажных русских изданий.
    covers: str | None = None


FILM_RATINGS = ("mdblist", "omdb", "kinopoisk")

ROUTES: dict[Kind, Route] = {
    Kind.MOVIE: Route(("tmdb",), "tmdb", FILM_RATINGS),
    Kind.SERIES: Route(("tmdb",), "tmdb", FILM_RATINGS),
    Kind.GAME: Route(("steam", "gog", "old_games"), None, ()),
    Kind.BOOK: Route(("google_books",), "google_books", (), covers="fantlab"),
    Kind.MUSIC: Route(("deezer",), "deezer", ()),
}


@dataclass(slots=True)
class Sources:
    """Поднятые клиенты и соединения под ними.

    Соединения перечислены здесь, а не собираются по клиентам: иначе реестру
    пришлось бы читать их приватное поле, а каждому клиенту — заводить пару
    свойств ради одного этого места."""

    tmdb: TmdbClient
    steam: SteamClient
    gog: GogClient
    old_games: OldGamesClient
    google_books: GoogleBooksClient
    deezer: DeezerClient
    fantlab: FantLabClient
    mdblist: MdbListClient
    omdb: OmdbClient
    kinopoisk: KinopoiskClient
    connections: tuple[SourceHttp, ...]

    def catalog_for(self, kind: Kind) -> list:
        """Порядок значим: он задаёт, чью выдачу человек увидит первой при равном
        числе кандидатов.

        У игр три равноправных источника, и покрытие даёт их сумма, а не каждый
        по отдельности: Steam и GOG — витрины и знают только то, что продаётся
        сегодня, old-games.ru закрывает ретро. «Дюны» нет ни в одной из витрин
        вовсе. Одну игру из двух-трёх источников склеивает `service/merging.py`;
        что не склеилось, остаётся на глазах человека — он убирает лишнее сам.

        У книг источник один: у Open Library народная разметка, а Goodreads
        закрыл выдачу ключей в 2020. У музыки тоже один — Deezer: ключа не
        требует вовсе, обложка у него 1000×1000, а треки приезжают вместе с
        карточкой."""
        return [getattr(self, name) for name in ROUTES[kind].catalogs]

    def people_for(
        self, kind: Kind
    ) -> TmdbClient | GoogleBooksClient | DeezerClient | None:
        """Кто умеет искать по человеку. У игр — никто, и это замерено, а не
        предположено: Steam по разработчику отдаёт разметку витрины, GOG молча
        игнорирует параметр и возвращает весь каталог. Людей же магазины не
        отдают вовсе, только компании.

        У книг отвечает тот же Google Books: своей ручки людей у него нет, и
        автор ищется той же выдачей оператором `inauthor:` — идентичность автора
        равна его имени. У музыки отвечает Deezer, и у него идентичность
        исполнителя настоящая: `artist.id` и своя ручка его альбомов."""
        name = ROUTES[kind].people
        return getattr(self, name) if name else None

    def covers_for(self, kind: Kind) -> FantLabClient | None:
        """Кто ищет обложку, когда каталог её не дал. У книг это FantLab,
        у остальных никто: их источники обложку отдают сами.

        Каталог FantLab — фантастика и смежное, и обычной прозы там не
        найдётся; это принятое ограничение, а не недоделка."""
        name = ROUTES[kind].covers
        return getattr(self, name) if name else None

    def client_for(self, source: Source):
        """Каталожный клиент по источнику карточки. У ручной карточки его нет и
        быть не может: она ниоткуда не приезжает."""
        return {
            Source.TMDB: self.tmdb,
            Source.STEAM: self.steam,
            Source.GOG: self.gog,
            Source.OLD_GAMES: self.old_games,
            Source.GOOGLE_BOOKS: self.google_books,
            Source.DEEZER: self.deezer,
        }.get(source)

    def rating_sources(self, kind: Kind) -> list:
        """У игр оценки приходят вместе с карточкой — из Steam и GOG. Своего
        агрегатора им не нужно: ни ключа, ни запроса, ни квоты. У книг и музыки
        агрегаторов нет и не предвидится: Goodreads закрыл выдачу ключей в 2020,
        у LiveLib публичного API нет."""
        return [getattr(self, name) for name in ROUTES[kind].ratings]

    async def aclose(self) -> None:
        for one in self.connections:
            await one.aclose()
