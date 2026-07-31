"""Подставные заменители внешнего мира: клиенты источников, транспорты, часы.

Транспорты лежат здесь, а не у тестов источников: их берут четыре теста вне
той папки, а второй адрес того же помощника означал бы два способа его найти.
`FakeClock` переехал по другому доводу — он не транспорт и не про записанные
ответы, а прежний его дом именно про них."""

from datetime import datetime, timedelta

import httpx

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


class FakeClock:
    """Часы, которые двигают руками: иначе срок предохранителя проверяется
    только `sleep`-ом на минуту."""

    def __init__(self) -> None:
        self.now = datetime(2026, 7, 27, 12, 0)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, delta: timedelta) -> None:
        self.now += delta


def responding(status: int = 200, *, json=None, text=None, content=None,
               headers=None):
    """Транспорт, отвечающий одним и тем же ответом на любой запрос.

    Тело здесь сочиняется, и это законно ровно там, где записать его нечем:
    квоту и частоту ни у одного источника не выбирали. Записанные ответы
    отдаёт `replay`, и он же ставит их настоящий код.

    `content` — тело байтами: у обложки оно картинка, а не текст."""
    return httpx.MockTransport(
        lambda request: httpx.Response(
            status, json=json, text=text, content=content, headers=headers or {}
        )
    )


def counting(transport: httpx.MockTransport):
    """Тот же транспорт, но помнит, сколько раз в него сходили.

    Заведено на одиннадцати рукописных счётчиках в шести модулях: везде
    проверяется одно и то же — что после взведённого предохранителя второй
    запрос в сеть не ушёл. Готовые `responding` и `capture` не подходили порознь:
    первый не считает, второй сам сочиняет тело, а тут нужно и своё тело, и
    счёт. Обёртка складывает их: телом занимается вложенный транспорт, счётом —
    эта."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return transport.handler(request)

    return httpx.MockTransport(handler), seen


def unreachable() -> httpx.MockTransport:
    """Транспорт, до которого не дозвонились: сеть отвечает не кодом, а ничем, и
    отказ по ней наверху решается иначе, чем непонятный ответ."""
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("не дозвонились")

    return httpx.MockTransport(handler)


def capture(*, content: bytes | None = None, status: int = 200):
    """Запоминает ушедшее на провод: проверять надо запрос, а не намерение.

    `content` — тело ответа байтами, когда запрашивают картинку: пустой JSON
    вместо неё сам стал бы отказом, и проверка адреса на него не добралась бы.
    `status` нужен там, где проверяется отказ: тело при этом всё равно
    возвращается, но до него дело не доходит."""
    return counting(
        responding(status, json={}) if content is None
        else responding(status, content=content)
    )
