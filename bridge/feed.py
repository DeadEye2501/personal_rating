"""Мост: лента — страницы разделов и гистограмма."""

from backend.model import Feed, Filters, Kind, Order, Section, Sort
from bridge.answer import Domain

# Шесть кортежей `Filters` — по два на признак: включённые и исключённые.
# Перечислены поимённо, потому что имя поля и есть контракт со страницей.
FILTER_FIELDS = ("tag_ids", "genre_ids", "scores",
                 "excluded_tag_ids", "excluded_genre_ids", "excluded_scores")


class FeedBridge(Domain):
    """Имя с хвостом, потому что `Feed` — это тип модели, и второе значение у
    того же слова путало бы обе стороны.

    Номер операции несут все четыре метода: смена фильтра или сортировки заводит
    новый запрос, и ответ прежнего приезжать не должен — ни страницей карточек,
    ни столбцами гистограммы, ни синопсисом карточки, уехавшей с экрана вместе с
    разделом.

    Сборка запроса идёт внутри заявки, а не до неё: неизвестный раздел или
    критерий сортировки — это `ValueError`, и снаружи оболочки он ушёл бы через
    границу потоков в pywebview, где ловить его некому."""

    def page(self, op: int, feed: dict, offset: int, limit: int) -> dict:
        return self._reply(
            lambda back: back.feed.page(_feed(feed), offset, limit), op=op)

    def views_of(self, op: int, item_ids: list) -> dict:
        """Точечное чтение после правки идёт той же дверью, что и лента."""
        return self._reply(lambda back: back.feed.views_of(item_ids), op=op)

    def synopsis(self, op: int, item_id: int) -> dict:
        """Синопсис показанной карточки: лента его не возит вовсе, и привозит
        его второй круг — тот же, что и оценки агрегаторов.

        Поштучно, а не пачкой на порцию: в порции пятьдесят карточек, а на
        экране их четыре, и платить за остальные незачем.

        Своего объявления в бэкенде у этого нет и не заведено: строку по номеру
        читает `library.get`, которым правка карточки уже пользуется отсюда же
        (`bridge/library.py:_over`)."""
        return self._reply(lambda back: _text(back, item_id), op=op)

    def histogram(self, op: int, kind: str, filters: dict) -> dict:
        """Тот же отфильтрованный набор, что и у разделов с карточками."""
        return self._reply(
            lambda back: back.feed.histogram(Kind(kind), _filters(filters)),
            op=op)


async def _text(back, item_id: int) -> str:
    """Синопсис строки или пусто, если строки нет: удалить карточку человек мог
    ровно между показом и вопросом о ней, и ронять из-за этого показ незачем."""
    card = await back.library.get(item_id)
    return card.synopsis if card is not None else ""


def _feed(feed: dict) -> Feed:
    order = feed["order"]
    return Feed(
        section=Section(feed["section"]),
        kind=Kind(feed["kind"]),
        filters=_filters(feed["filters"]),
        # Сторона приходит всегда: у переключателя сортировки её не бывает
        # неназванной, а умолчание вторым местом разъехалось бы с моделью молча.
        order=Order(key=Sort(order["key"]), descending=order["descending"]),
    )


def _filters(filters: dict) -> Filters:
    """Страница шлёт только то, что человек тронул: неназванный признак — это
    отсутствие фильтра, а не пустой набор."""
    return Filters(**{name: tuple(filters.get(name, ()))
                      for name in FILTER_FIELDS})
