"""Подставные клиенты источников и реестр над ними."""

from backend.model import Kind, Source


class FakeClient:
    """Клиент источника с заданным ответом.

    Что у него спрашивают, дописывают наследники: у каталожного это выдача
    поиска и детальная карточка, у перезапроса — сезоны с сериями. Общее у всех
    трёх одно: заданный исход, имя источника для отказа и список того, о чём
    спросили."""

    def __init__(self, outcome, name: str = "tmdb") -> None:
        self.outcome = outcome
        self.name = name
        self.asked = []


class FakeCatalog(FakeClient):
    """Спрашивают у него детальную карточку. Наследники дописывают остальное:
    у GOG к ней добавляется номер по слагу."""

    async def card(self, source_id: str, kind: Kind):
        self.asked.append((source_id, kind))
        return self.outcome


class FakeSources:
    """Реестр с заданными каталожными клиентами. Настоящий поднимает шесть
    клиентов, у каждого свой SSL-контекст, — а сервису поиска нужен от него
    только список тех, кого спрашивать."""

    def __init__(self, *clients) -> None:
        self._clients = list(clients)

    def catalog_for(self, _kind: Kind) -> list:
        """Тип содержимого настоящий реестр разбирает сам, и проверяется он в
        его собственных тестах: здесь важно только, кого он вернул."""
        return self._clients

    def client_for(self, _source: Source):
        """Тот же довод про источник: подмену клиента источнику сторожат тесты
        самого реестра. Без клиентов — `None`, как у ручной карточки."""
        return self._clients[0] if self._clients else None

    def rating_sources(self, kind: Kind) -> list:
        """Единственное правило настоящего реестра, которое здесь повторяется:
        у игр оценочных источников нет. Без него сервис не проверить на пустом
        списке, а сам список — предмет его работы."""
        return [] if kind is Kind.GAME else self._clients
