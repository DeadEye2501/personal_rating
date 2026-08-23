"""Подставные заменители внешнего мира: клиенты источников, транспорты, часы.

Транспорты лежат здесь, а не у тестов источников: их берут четыре теста вне
той папки, а второй адрес того же помощника означал бы два способа его найти.
`FakeClock` переехал по другому доводу — он не транспорт и не про записанные
ответы, а прежний его дом именно про них."""

from datetime import datetime, timedelta

import httpx

from backend.model import Found, Kind, Source


class FakeClient:
    """Клиент источника с заданным ответом.

    Что у него спрашивают, дописывают наследники: у каталожного детальную
    карточку, у поискового — выдачу, у перезапроса — сезоны с сериями, у
    оценочного — чужие оценки. Общее у всех четверых одно: заданный исход, имя
    источника для отказа и список того, о чём спросили."""

    def __init__(self, outcome, name: str = "tmdb") -> None:
        self.outcome = outcome
        self.name = name
        self.asked: list[tuple] = []


class FakeCatalog(FakeClient):
    """Спрашивают у него детальную карточку. Наследники дописывают остальное:
    у GOG к ней добавляется номер по слагу."""

    async def card(self, source_id: str, kind: Kind):
        self.asked.append((source_id, kind))
        return self.outcome


class FakeSearch(FakeClient):
    """Клиент, у которого спрашивают выдачу: по названию, по имени человека и
    работы найденного.

    Три ручки — три заданных исхода: у настоящего TMDB это три разных запроса, и
    слепив их в один, тест не различил бы, какая половина привезла находку.
    Магазинам достаётся одна ручка из трёх, и это не поблажка фикстуре: людей
    они не отдают вовсе."""

    def __init__(self, outcome=None, name: str = "tmdb", *,
                 people=None, works=None, pages: bool = True) -> None:
        super().__init__(outcome, name)
        self.people = people
        self.works = works
        # Умолчание истинно, потому что листает большинство настоящих: TMDB,
        # Google Books и Deezer. Нелистающий называется явно — тем же признаком,
        # каким его объявляет свой клиент.
        self.PAGES = pages

    async def search(self, query: str, kind: Kind, offset: int = 0):
        """Заданное исключение он бросает, а не возвращает: сервис обязан
        пережить и это.

        Смещение записывается вместе с запросом: без него «спросили вторую
        порцию» неотличимо от «спросили первую дважды»."""
        self.asked.append((query, kind, offset))
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome

    async def find_people(self, name: str):
        self.asked.append(("find_people", name))
        if isinstance(self.people, BaseException):
            raise self.people
        return self.people

    async def credits_of(self, person_id: str, kind: Kind):
        """Словарём задают ответы, когда тёзок несколько и работы у них
        разные."""
        self.asked.append(("credits_of", person_id, kind))
        if isinstance(self.works, dict):
            return self.works.get(person_id, Found([]))
        return self.works


class FakeSources:
    """Реестр с заданными каталожными клиентами. Настоящий поднимает девять
    клиентов, у каждого свой SSL-контекст, — а сервису поиска нужен от него
    только список тех, кого спрашивать."""

    # Три набора, и каждый полон: правило целиком лежит в наборе, а не половиной
    # в наборе и половиной в условии — иначе одно правило живёт в двух местах.
    # Сами правила живут в `Sources.ROUTES`, здесь они повторяются нарочно:
    # сервис обязан слушаться реестра, и без этих веток проверить его послушание
    # было бы нечем.
    #
    # Людей не отдают магазины — замерено; у остальных ответчик есть.
    NO_PEOPLE = frozenset({Kind.GAME})
    # Оценки у игр приезжают даром вместе с карточкой, у книг и музыки их нет и
    # не предвидится.
    NO_RATINGS = frozenset({Kind.GAME, Kind.BOOK, Kind.MUSIC})

    def __init__(self, *clients, covers=None) -> None:
        self._clients = list(clients)
        self.covers = covers

    def catalog_for(self, kind: Kind) -> list:
        """Тип содержимого настоящий реестр разбирает сам, и проверяется он в
        его собственных тестах: здесь важно только, кого он вернул.

        Ветки «у этого типа каталога нет» здесь больше нет: с восьмым источником
        каталог есть у всех пяти, и набор пустых типов стоял бы мёртвым."""
        return self._clients

    def people_for(self, kind: Kind):
        """Кто умеет искать по человеку. Правило «у игр — никто» повторяется
        отсюда нарочно: сервис обязан слушаться реестра, и без этой ветки
        проверить его послушание было бы нечем. Само правило живёт в
        `Sources.ROUTES`, там же и замер про магазины.

        У книг ответчик появился 23.08.2026 — тот же Google Books, — у музыки
        тем же днём Deezer; обе ветки отсюда ушли вместе с ними."""
        if kind in self.NO_PEOPLE:
            return None
        return self._clients[0]

    def covers_for(self, kind: Kind):
        """Кто ищет обложку, когда каталог её не дал. Правило реестра, которое
        здесь повторяется: запасной источник есть только у книг, и сервис обязан
        слушаться реестра — без этой ветки не проверить, что фильмам и играм он
        никого не спрашивает.

        Двойник подставляется отдельно: у него другая поверхность — одна ручка
        `cover_for`, — и путать его с каталожным клиентом нельзя."""
        return self.covers if kind is Kind.BOOK else None

    def client_for(self, _source: Source):
        """Тот же довод про источник: подмену клиента источнику сторожат тесты
        самого реестра. Без клиентов — `None`, как у ручной карточки."""
        return self._clients[0] if self._clients else None

    def rating_sources(self, kind: Kind) -> list:
        """Правило настоящего реестра, которое здесь повторяется: оценочных
        источников нет у игр, а у книг и музыки нет и не предвидится. Без него
        сервис не проверить на пустом списке, а сам список — предмет его
        работы."""
        if kind in self.NO_RATINGS:
            return []
        return self._clients


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
