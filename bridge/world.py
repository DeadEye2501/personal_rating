"""Мост: всё, что смотрит наружу, — привязка по ссылке, перезапрос сериала,
оценки агрегаторов и открытие страницы источника."""

import asyncio
import webbrowser
from datetime import datetime

from backend.model import Denied, Kind, Missing, Refusal, parse_link
from bridge.answer import Domain, stale
from bridge.kept import Kept
from bridge.wire import outcome


class BadLink(Denied):
    """Вставленное не похоже на адрес источника.

    Отказ моста, а не бэкенда, и всё-таки `Denied`: род отказа берётся из имени
    класса, и через него он доезжает до плашки тем же путём, что занятое имя
    тега. Отдельная ветка ответа завела бы шестой род мимо общего формата."""


class ForeignScheme(Denied):
    """Адрес не начинается с `https://`, а значит открывать его нельзя.

    Своим классом, а не голым предком: плашка называет причину по имени, и
    «отказано» без причины ничем не лучше молчания."""


class World(Domain):
    def __init__(self, thread) -> None:
        super().__init__(thread)
        self._kept = Kept()

    def parse(self, raw: str, kind: str | None) -> dict:
        """Зовётся на каждое нажатие клавиши, но не ходит ни в сеть, ни на диск.
        Переписывать разбор на JS нельзя: вторая регулярка на тот же адрес
        разошлась бы с первой молча.

        Идёт через оболочку, как и всё остальное, хотя бэкенд ей не нужен:
        отдельный путь наружу означал бы, что исключение из разбора летит через
        границу потоков мимо неё. Цена — переброс в поток без единого обращения
        к диску или сети."""
        return self._reply(lambda _back: _parsed(raw, kind))

    def card_for_link(self, op: int, raw: str, kind: str | None) -> dict:
        """Карточка помнится здесь: страница её не показывает, ей нужно только
        «нашлось» или «нет»."""
        return self._reply(lambda back: self._asked(back, op, raw, kind), op=op)

    def link(self, op: int, item_id: int, overwrite: bool) -> dict:
        """Внешнее заполняет только пустое; галочка «перезаписать данные» — на
        случай, когда карточка заводилась на скорую руку."""
        card = self._kept.taken(op)
        if card is None:
            return stale()
        now = datetime.now()
        return self._reply(
            lambda back: back.linker.link(item_id, card, now,
                                          overwrite=overwrite), op=op)

    def refresh_series(self, op: int, item_id: int) -> dict:
        """Тихо ничего не делает в трёх случаях — не сериал, не TMDB, не
        просрочено, — и различать их странице незачем."""
        return self._reply(lambda back: back.series.refresh(item_id), op=op)

    def enrich(self, op: int, item_id: int, kind: str) -> dict:
        """Только тому, что уже в базе: у кандидата нет `imdb_id`, он приходит
        лишь в детальном ответе."""
        return self._reply(
            lambda back: back.enricher.enrich(item_id, Kind(kind)), op=op)

    def expected(self, op: int, kind: str) -> dict:
        """Под неприехавшую оценку рисуется кружок, и сколько их будет, надо
        знать до ответа сети.

        Обёрнуто в корутину, а не отдано как есть: этот метод бэкенда
        **синхронный**, а поток кладёт фабрику в `create_task`, который от
        списка поднимает `TypeError`. Отвечено на это было бы «непредвиденный
        сбой» — вместо ответа, который есть и приезжает мгновенно."""
        return self._reply(lambda back: _expected(back, kind), op=op)

    def open(self, url: str) -> dict:
        """Страница источника открывается системным браузером.

        Обычная ссылка увела бы саму страницу приложения: окно — это Chromium
        без адресной строки и без кнопки «назад», и вернуться было бы нечем.
        Бэкенд ей не нужен, а поток нужен: у оболочки другого пути наружу нет,
        и без неё чужая схема адреса летела бы исключением через границу."""
        return self._reply(lambda _back: _opened(url))

    async def _asked(self, back, op, raw, kind):
        link = _link(raw, kind)
        card = await back.loader.card_for_link(link)
        if not isinstance(card, Missing | Refusal):
            # Помним только найденное. Привязка первым делом читает внешние
            # идентификаторы карточки, и «не нашлось» на этом месте дало бы
            # человеку невнятный сбой вместо ответа «связывать не с чем».
            self._kept.put(op, card)
        return outcome(card)


async def _parsed(raw: str, kind: str | None):
    return parse_link(raw, _kind(kind))


async def _expected(back, kind: str):
    return back.enricher.expected(Kind(kind))


async def _opened(url: str) -> None:
    # Только свои адреса: `webbrowser` отдаёт строку системе как есть, а схема
    # оттуда приходит с чужой страницы карточки.
    if not url.startswith("https://"):
        raise ForeignScheme(url)
    # Отдельным потоком, потому что при заданной переменной `BROWSER`
    # `webbrowser` берёт `GenericBrowser`, а тот ждёт закрытия браузера. В цикле
    # бэкенда это заморозило бы и ленту, и поиск, и обложки.
    await asyncio.to_thread(webbrowser.open, url)


def _link(raw: str, kind: str | None):
    """Разбор идёт внутри заявки, а не до неё: и перевод подсказки тумблера, и
    непохожее на адрес обязаны стать ответом, а не исключением через границу
    потоков."""
    link = parse_link(raw, _kind(kind))
    if link is None:
        raise BadLink(raw)
    return link


def _kind(kind: str | None) -> Kind | None:
    """Тип берётся из адреса, а подсказка тумблера нужна там, где его в адресе
    нет, — у голого идентификатора."""
    return Kind(kind) if kind else None
