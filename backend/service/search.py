"""Поиск карточек — по своей библиотеке и по чужим базам."""

from backend.model import CardView, Kind
from backend.storage.repository.library import LibraryRepository
from backend.storage.repository.views import ViewsRepository

# Ровно страница выдачи TMDB: одна порция стоит одного запроса. Величина —
# настройка, а не свойство схемы.
SEARCH_SIZE = 20


class SearchService:
    """Поиск идёт сразу по двум местам, и метод у каждого свой: своё отдаётся
    первым и работает без сети, внешнее доливается по готовности."""

    def __init__(self, library: LibraryRepository,
                 views: ViewsRepository) -> None:
        self._library = library
        self._views = views

    async def local(self, kind: Kind, query: str) -> list[CardView]:
        item_ids = await self._library.search(kind, query, limit=SEARCH_SIZE)
        return await self._views.in_order(item_ids)
