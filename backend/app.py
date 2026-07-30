"""Бэкенд, собранный целиком."""

from dataclasses import dataclass

import httpx

from backend.config import Config
from backend.model import Source
from backend.service.cards import CardWriter
from backend.service.enrich import Enricher
from backend.service.library import LibraryService
from backend.service.linking import Linker
from backend.service.loading import Loader
from backend.service.posters import PosterService
from backend.service.search import SearchService
from backend.sources.http import SourceHttp
from backend.sources.registry import Sources, build_sources
from backend.storage.posters import PosterStore
from backend.storage.repository.credits import CreditRepository, companies, people
from backend.storage.repository.external import (
    ExternalIdsRepository,
    ExternalRatingsRepository,
)
from backend.storage.repository.genres import GenresRepository
from backend.storage.repository.library import LibraryRepository
from backend.storage.repository.ratings import RatingsRepository
from backend.storage.repository.sections import SectionsRepository
from backend.storage.repository.tags import TagsRepository
from backend.storage.repository.views import ViewsRepository
from backend.storage.repository.wishlist import WishlistRepository
from backend.storage.session import create_engine, session_factory


@dataclass(slots=True)
class Backend:
    """Всё, что клиент может спросить. Один объект вместо десятка ссылок,
    которые пришлось бы тащить через границу потоков поодиночке."""

    library: LibraryRepository
    ratings: RatingsRepository
    tags: TagsRepository
    wishlist: WishlistRepository
    genres: GenresRepository
    people: CreditRepository
    companies: CreditRepository
    ids: ExternalIdsRepository
    external_ratings: ExternalRatingsRepository
    # Одна карточка по идентификатору: после загрузки кандидата и после
    # простановки оценки ленте надо перерисовать её, а не всю страницу.
    views: ViewsRepository

    search: SearchService
    feed: LibraryService
    loader: Loader
    enricher: Enricher
    linker: Linker
    posters: PosterService
    sources: Sources

    _engine: object

    async def aclose(self) -> None:
        """Закрыть могут и владелец, и фикстура теста — второй раз это тихо.

        Своего флага для этого нет: все трое закрываются повторно молча, и
        сторожит это проверка, а не ветка, которую нечем уронить."""
        await self.sources.aclose()
        await self.posters.aclose()
        await self._engine.dispose()


async def build_backend(
    config: Config, transport: httpx.AsyncBaseTransport | None = None
) -> Backend:
    """Единственное место, где бэкенд собирается целиком.

    Транспорт внедряется ради тестов: без него каждый клиент поднимает
    настоящий `AsyncClient` со своим SSL-контекстом.

    Схему база получает миграциями, а не отсюда: `alembic upgrade head`.

    Папку данных заводить не нужно: её создаёт `create_engine`, и он идёт
    первым — до того, как за файл возьмётся хранилище постеров."""
    engine = create_engine(config.library_db)
    sessions = session_factory(engine)

    store = PosterStore(config.posters_db)
    await store.open()

    sources = build_sources(config, transport=transport)
    # Своя ветка на источник: у каждого свой предохранитель и свой заголовок.
    posters = PosterService(
        {
            Source.TMDB: SourceHttp("tmdb-poster", transport=transport),
            Source.STEAM: SourceHttp("steam-poster", transport=transport),
            Source.GOG: SourceHttp("gog-poster", transport=transport),
        },
        store,
    )

    library = LibraryRepository(sessions)
    genres = GenresRepository(sessions)
    person_repository = people(sessions)
    company_repository = companies(sessions)
    ids = ExternalIdsRepository(sessions)
    external_ratings = ExternalRatingsRepository(sessions)
    views = ViewsRepository(sessions)

    # Писатель и привязка собираются из одного и того же: у них общая основа
    # `CardParts`, и набор из семи имён должен совпадать у обоих буквально.
    parts = {
        "library": library,
        "genres": genres,
        "people": person_repository,
        "companies": company_repository,
        "ids": ids,
        "ratings": external_ratings,
        "posters": posters,
    }

    return Backend(
        library=library,
        ratings=RatingsRepository(sessions),
        tags=TagsRepository(sessions),
        wishlist=WishlistRepository(sessions),
        genres=genres,
        people=person_repository,
        companies=company_repository,
        ids=ids,
        external_ratings=external_ratings,
        views=views,
        search=SearchService(library=library, views=views, sources=sources,
                             genres=genres),
        feed=LibraryService(SectionsRepository(sessions), views),
        loader=Loader(library=library, writer=CardWriter(**parts),
                      sources=sources, posters=posters),
        enricher=Enricher(sources=sources, ids=ids, ratings=external_ratings),
        linker=Linker(**parts),
        sources=sources,
        posters=posters,
        _engine=engine,
    )
