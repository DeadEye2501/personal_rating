"""Бэкенд, собранный целиком."""

from dataclasses import dataclass
from datetime import datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncEngine

from backend.config import Config
from backend.model import Item, Kind, Source
from backend.service.cards import CardWriter
from backend.service.creation import fresh_item
from backend.service.enrich import Enricher
from backend.service.library import LibraryService
from backend.service.linking import Linker
from backend.service.loading import Loader
from backend.service.people import PeopleSearch
from backend.service.posters import POSTER_SOURCES, PosterService
from backend.service.removal import discard_card
from backend.service.search import SearchParts, SearchService
from backend.service.series import SeriesRefresh
from backend.sources.build import build_sources
from backend.sources.http import SourceHttp, poster_name
from backend.sources.registry import Sources
from backend.storage.posters import PosterStore
from backend.storage.repository.credits import CreditRepository, companies, people
from backend.storage.repository.external import (
    ExternalIdsRepository,
    ExternalRatingsRepository,
)
from backend.storage.repository.genres import GenresRepository
from backend.storage.repository.library import LibraryRepository
from backend.storage.repository.ratings import RatingsRepository
from backend.storage.repository.removed import RemovedRepository
from backend.storage.repository.sections import SectionsRepository
from backend.storage.repository.tags import TagsRepository
from backend.storage.repository.views import ViewsRepository
from backend.storage.repository.wishlist import WishlistRepository
from backend.storage.rescale import apply_scale
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

    search: SearchService
    finder: PeopleSearch
    feed: LibraryService
    loader: Loader
    series: SeriesRefresh
    enricher: Enricher
    linker: Linker
    posters: PosterService

    # Ступеней в своей оценке. Число, а не репозиторий: страница рисует по нему
    # ряд звёзд, и спрашивает его один раз при загрузке.
    scale: int

    # Наружу не отдаётся: клиенту знать об удалённом нечего — он видит
    # следствие, отсеянную выдачу. Зовут его двое, и оба здесь.
    _removed: RemovedRepository
    _sources: Sources
    _engine: AsyncEngine

    async def create_manual_card(self, item: Item, now: datetime) -> int:
        """Заведённая руками карточка сразу ложится в список дел: решение
        пользователя 02.08.2026.

        Иначе она не показывается нигде — в «Оценённые» её не пускает
        отсутствие оценки, — и найти сохранённое можно только поиском по своей
        базе.

        Метод здесь, а не у репозитория библиотеки: закладка живёт в соседней
        таблице со своим репозиторием, и требовать его от вызывающего значило бы
        менять правило заведения в каждом, кто заводит. Заводит его один — мост,
        по кнопке «+»; кандидат выдачи и карточка от источника идут общим
        `fresh_item` мимо этого метода и закладки не получают."""
        item_id = await fresh_item(self.library, self.posters, item)
        await self.wishlist.add(item_id, now)
        return item_id

    async def delete_card(self, item_id: int) -> None:
        """Карточка целиком, вместе с обложкой из второго файла базы.

        Метод здесь, а не у репозитория: удаление — это две базы в строго
        определённом порядке, и репозиторий одной из них не должен требовать от
        клиента вторую. Порядок и память об убранном заданы в
        `service/removal.py`: там же записано, почему помнит именно этот путь, а
        не общий `remove_card`, которым откатывается сорвавшаяся запись."""
        await discard_card(self.library, self.posters, self._removed, item_id)

    async def restore_removed(self, kind: Kind, source: Source,
                              source_id: str) -> None:
        """Снять пометку об удалении. Карточка при этом не возвращается — её
        нет, — игра просто снова находится поиском.

        Метод здесь по той же причине, что и `delete_card`: память об убранном
        клиенту не открыта, она приватная. Иначе поток интерфейса дотянулся бы
        до репозитория напрямую."""
        await self._removed.forget(kind, source, source_id)

    async def aclose(self) -> None:
        """Закрыть могут и владелец, и фикстура теста — второй раз это тихо.

        Своего флага для этого нет: все трое закрываются повторно молча, и
        сторожит это проверка, а не ветка, которую нечем уронить."""
        await self._sources.aclose()
        await self.posters.aclose()
        await self._engine.dispose()


def card_parts(sessions, posters: PosterService) -> dict:
    """Семь частей одной карточки. Писатель и привязка собираются из одного и
    того же — у них общая основа `CardParts`, — и набор имён у них обязан
    совпадать буквально, поэтому перечислен он здесь, а не у каждого сборщика."""
    return {
        "library": LibraryRepository(sessions),
        "genres": GenresRepository(sessions),
        "people": people(sessions),
        "companies": companies(sessions),
        "ids": ExternalIdsRepository(sessions),
        "ratings": ExternalRatingsRepository(sessions),
        "posters": posters,
    }


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
    # До первого запроса: шкала могла смениться, и лента, гистограмма и звёзды
    # обязаны увидеть уже переведённые оценки.
    await apply_scale(sessions, config.scale)

    store = PosterStore(config.posters_db)
    await store.open()

    sources = build_sources(config, transport=transport)
    # Своя ветка на источник: у каждого свой предохранитель и свой заголовок.
    posters = PosterService(
        {source: SourceHttp(poster_name(source), transport=transport)
         for source in POSTER_SOURCES},
        store,
    )

    parts = card_parts(sessions, posters)
    # `library` и `genres` дальше нужны и `Backend`, и сервисам, два последних —
    # только обогащению. Второе называется вслух потому, что имена совпали, а
    # предметы разные: у `parts` это оценки агрегаторов, у `Backend.ratings` — свои.
    library = parts["library"]
    genres = parts["genres"]
    removed = RemovedRepository(sessions)
    ids = parts["ids"]
    external_ratings = parts["ratings"]
    views = ViewsRepository(sessions)

    return Backend(
        library=library,
        ratings=RatingsRepository(sessions),
        tags=TagsRepository(sessions),
        wishlist=WishlistRepository(sessions),
        genres=genres,
        people=parts["people"],
        companies=parts["companies"],
        search=SearchService(library=library, views=views, sources=sources,
                             parts=SearchParts(genres=genres, removed=removed)),
        finder=PeopleSearch(views=views, people=parts["people"],
                            companies=parts["companies"], sources=sources,
                            parts=SearchParts(genres=genres, removed=removed)),
        feed=LibraryService(SectionsRepository(sessions, config.scale), views),
        loader=Loader(library=library, writer=CardWriter(**parts),
                      sources=sources, posters=posters),
        series=SeriesRefresh(library=library, sources=sources),
        enricher=Enricher(sources=sources, ids=ids, ratings=external_ratings),
        linker=Linker(**parts),
        posters=posters,
        scale=config.scale,
        _removed=removed,
        _sources=sources,
        _engine=engine,
    )
