"""Общее у проверок третьего круга: подставные оценочные клиенты и карточка.

Своим модулем, а не в `conftest.py`: поверхность общего там ведётся списком и
растёт от каждого переезда, а этими шестью пользуются ровно два соседних модуля
проверок — оценки и идентификаторы."""


from backend.model import (
    ExternalRating,
    Found,
    Kind,
    Ratings,
)
from backend.storage.repository.external import (
    ExternalRatingsRepository,
)
from tests.conftest import MOMENT, FakeClient


class FakeRatings(FakeClient):
    """Оценочный клиент: что он умеет привозить, объявлено списком, как у
    настоящих."""

    def __init__(self, provides, outcome, name: str = "mdblist") -> None:
        super().__init__(outcome, name)
        self.PROVIDES = provides

    async def ratings(self, imdb_id: str, kind: Kind):
        self.asked.append((imdb_id, kind))
        return self.outcome

class Breaking(FakeRatings):
    """Клиент, падающий не тем, что клиенты ловят: так выглядит наша опечатка или
    чужая библиотека. Провод и разбор клиент разбирает сам и отдаёт отказом."""

    async def ratings(self, imdb_id: str, kind: Kind):
        self.asked.append((imdb_id, kind))
        raise KeyError("payload")


def found(*pairs) -> Found:
    return Found(Ratings(values=tuple(
        ExternalRating(source, value, MOMENT) for source, value in pairs
    )))

async def stored_ratings(sessions, item_id) -> dict:
    rows = await ExternalRatingsRepository(sessions).ratings_of(item_id)
    return {row.source: row.value for row in rows}
