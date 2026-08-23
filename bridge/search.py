"""Мост: поиск — своё, чужое, складывание, заведение найденного.

Единственный домен со своей механикой, и вся она из одного: `CardView` уезжает на
страницу словарём, а обратно не собирается. Поэтому выдачу мост помнит, а
страница называет кандидата парой «источник + идентификатор»."""

from backend.model import SEARCH_SIZE, ExternalSearch, Kind, merge_results
from bridge.answer import Domain, stale
from bridge.kept import Kept
from bridge.wire import outcome


class Search(Domain):
    def __init__(self, thread) -> None:
        super().__init__(thread)
        self._kept = Kept()
        # Номер операции, запрос и сколько строк уже спрошено у источника.
        # Смещение помнит мост, а не страница: тогда странице не нужно знать ни
        # размера порции, ни арифметики — она зовёт `external` столько раз,
        # сколько надо, и читает признак «есть ещё».
        self._asked: tuple[int, str, str, int] | None = None

    def local(self, op: int, kind: str, query: str) -> dict:
        """Своё показывается сразу: локальная база отвечает за миллисекунды.

        Запрос запоминается строкой, а переводится в тип внутри заявки: перевод
        снаружи оболочки ушёл бы исключением через границу потоков.

        Вместе с номером, а не сам по себе: pywebview зовёт каждый метод в своём
        потоке, и допечатанная строка попадает сюда, пока первый шаг прежней
        операции ещё едет. Своей выдачи она в этот миг не запомнила, так что по
        ней старый второй шаг не отсечь, — и он ушёл бы в сеть с чужой строкой."""
        self._asked = (op, kind, query, 0)
        return self._reply(lambda back: self._own(back, op, kind, query), op=op)

    def external(self, op: int) -> dict:
        """Внешнее доливается по готовности и складывается со своим здесь:
        `merge_results` живёт в модели ровно потому, что складывать приходится
        клиенту, и второго его объявления быть не должно.

        Запрос снимается здесь, а не внутри заявки: pywebview зовёт каждый метод
        в своём потоке, и к моменту ответа человек мог допечатать строку.

        Зовётся столько раз, сколько прокрутка просит ещё: смещение мост
        двигает сам, на порцию за вызов. Двигает **до** ответа, а не после:
        pywebview зовёт каждый метод в своём потоке, и два «дай ещё» подряд
        иначе ушли бы за одной и той же порцией.

        Пустая память запроса — это выдача по клику на имя: у неё второго шага
        нет вовсе, и разворачивать тут нечего. Без проверки это `TypeError` за
        пределами заявки, то есть исключение через границу потоков."""
        if self._kept.taken(op) is None or self._asked is None:
            return stale()
        asked_op, kind, query, offset = self._asked
        if asked_op != op:
            return stale()
        self._asked = (asked_op, kind, query, offset + SEARCH_SIZE)
        return self._reply(
            lambda back: self._outer(back, op, kind, query, offset), op=op)

    def by_person(self, op: int, domain: str, entity_id: int,
                  kind: str) -> dict:
        """Выдача по клику на имя — обычная выдача поиска, и помнится она так
        же: из неё добавляют карточку тем же `ensure`. Имя бывает и студией —
        домен приезжает доводом, поэтому у бэкенда ручка и зовётся `by_entity`.

        Запрос не запоминается: второго шага у клика нет — обе половины
        приезжают собранными, и `external` за ним не зовётся вовсе."""
        return self._reply(
            lambda back: self._person(back, op, domain, entity_id, Kind(kind)),
            op=op)

    def ensure(self, op: int, source: str, source_id: str) -> dict:
        """Кандидат берётся из помнимой выдачи: `CardView` собрать из JSON
        нечем, а пара переживает перерисовку списка."""
        candidate = _found(self._kept.taken(op), source, source_id)
        if candidate is None:
            return stale()
        return self._reply(
            lambda back: self._added(back, candidate), op=op)

    async def _own(self, back, op, kind, query):
        """Перевод в JSON делает оболочка, и делает его один раз: отсюда наружу
        уходят датаклассы."""
        views = list(await back.search.local(Kind(kind), query))
        self._kept.put(op, views)
        return views

    async def _outer(self, back, op, kind, query, offset):
        """Странице уезжает **приращение**, а память копит всё.

        Приращение потому, что лента дописывает приехавшее в конец: отдай он
        накопленное — вторая порция склеила бы выдачу саму с собой. Память копит
        всё потому, что из неё заводят кандидата (`ensure` ищет его в `Kept`), и
        строка первой порции обязана заводиться и после приезда второй."""
        shown = self._kept.taken(op) or []
        found = await back.search.external(Kind(kind), query, offset)
        merged = merge_results(shown, list(found.views))
        if self._kept.taken(op) is not None:
            # Пока летел ответ, страница могла набрать новую строку и захватить
            # ячейку под свою выдачу. Затереть её собой значит отнять у новой
            # операции её собственную половину — ту, где оценки, теги и закладка.
            self._kept.put(op, merged)
        # Признак переносится поимённо, а не наследуется: ответ тут собирается
        # заново, и всякое новое поле `ExternalSearch` теряется в такой сборке
        # молча — у него есть умолчание. Страница ветвится по этому признаку, и
        # без него список убранного нарисовался бы обычными карточками ленты.
        return ExternalSearch(views=tuple(merged[len(shown):]),
                              refusals=found.refusals,
                              removed=found.removed, more=found.more)

    async def _person(self, back, op, domain, entity_id, kind):
        answer = await back.finder.by_entity(domain, entity_id, kind)
        self._kept.put(op, list(answer.views))
        return answer

    async def _added(self, back, candidate):
        return outcome(await back.loader.ensure(candidate))


def _found(views, source: str, source_id: str):
    if not views:
        return None
    for view in views:
        if view.source == source and view.source_id == source_id:
            return view
    return None
