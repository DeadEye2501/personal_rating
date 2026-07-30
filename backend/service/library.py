"""Страницы разделов и гистограмма для показа."""

from backend.model import CardView, Feed, Filters, Histogram, Kind
from backend.storage.repository.sections import SectionsRepository
from backend.storage.repository.views import ViewsRepository

# Лента читается с диска и стоит дёшево. Величина — настройка, а не свойство
# схемы: меняется этой строкой.
PAGE_SIZE = 50


class LibraryService:
    """«Оценённые» и «Хочу посмотреть» отличаются только тем, что спрашивают у
    базы, — поэтому метод у них один. Поиск сюда не ходит: он спрашивает не
    базу.

    Гистограмма лежит рядом со страницей, хотя своей работы у неё здесь нет:
    показывает их один экран и по одному отфильтрованному набору, а через
    границу слоёв клиент репозитории не видит вовсе. Отдельный класс на один
    проброс был бы абстракцией без второй реализации."""

    def __init__(self, sections: SectionsRepository,
                 views: ViewsRepository) -> None:
        self._sections = sections
        self._views = views

    async def page(self, feed: Feed, offset: int = 0,
                   limit: int = PAGE_SIZE) -> list[CardView]:
        item_ids = await self._sections.ids(feed, limit=limit, offset=offset)
        return await self.views_of(item_ids)

    async def views_of(self, item_ids: list[int]) -> list[CardView]:
        """Готовая лента по готовому списку номеров.

        Ею пользуются двое: страница «всё с этим человеком», где что показывать
        решил репозиторий связей, и перерисовка одной карточки — после загрузки
        кандидата и после простановки оценки ленте нужна она одна, а не вся
        страница."""
        return await self._views.in_order(item_ids)

    async def histogram(self, kind: Kind, filters: Filters) -> Histogram:
        return await self._sections.histogram(kind, filters)
