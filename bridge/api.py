"""Поверхность моста: семь доменов и отмена.

pywebview собирает её рефлексией — `dir()` без имён с подчёркиванием, с
рекурсией в объекты, — и имена с точкой на стороне страницы разворачиваются в
дерево: `pywebview.api.feed.page(...)`."""

from bridge.answer import Domain
from bridge.covers import Covers
from bridge.feed import FeedBridge
from bridge.library import Library
from bridge.marks import Marks
from bridge.refs import Refs
from bridge.search import Search
from bridge.world import World


class Api(Domain):
    """Отмена лежит на корне, а не в домене: страница уходит целиком и гасит всё,
    что начала, одним пересечением границы.

    Наследует оболочку ради неё же: `ops` приходит из JSON, и на не-списке обход
    поднял бы исключение прямо в теле вызова — странице приехал бы отклонённый
    промис, то есть третий вид ответа, которого у моста не бывает."""

    def __init__(self, thread) -> None:
        super().__init__(thread)
        self.library = Library(thread)
        self.marks = Marks(thread)
        self.refs = Refs(thread)
        self.feed = FeedBridge(thread)
        self.search = Search(thread)
        self.world = World(thread)
        self.covers = Covers(thread)

    def cancel(self, ops: list) -> dict:
        """Неизвестный номер — обычное дело: ответ мог прийти раньше отмены."""
        return self._reply(lambda _back: self._cancelled(ops))

    async def _cancelled(self, ops: list) -> None:
        self._thread.cancel(list(ops))
