"""Что показывает раздел."""

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
    показывает их один экран и по одному отфильтрованному набору. Отдельный класс
    на один проброс был бы абстракцией без второй реализации."""

    def __init__(self, sections: SectionsRepository,
                 views: ViewsRepository) -> None:
        self._sections = sections
        self._views = views

    async def page(self, feed: Feed, offset: int = 0,
                   limit: int = PAGE_SIZE) -> list[CardView]:
        item_ids = await self._sections.ids(feed, limit=limit, offset=offset)
        return await self.views_of(item_ids)

    async def views_of(self, item_ids: list[int]) -> list[CardView]:
        """Готовая лента по готовому списку номеров: что показывать, решил тот,
        кто этот список составил.

        Отсюда её берёт `page`. Сам `ViewsRepository` на поверхности `Backend` не
        лежит, но правила «клиент репозиториев не видит» у проекта нет — семь
        других лежат; разбор этой развилки в `docs/deferred.md`."""
        return await self._views.in_order(item_ids)

    async def histogram(self, kind: Kind, filters: Filters) -> Histogram:
        return await self._sections.histogram(kind, filters)
