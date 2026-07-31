"""Двойники бэкенда и потоки на них.

Настоящий `Backend` здесь не собирается ни разу: у него база, миграции и шесть
клиентов сети, а проверяется тут граница потоков и мост, а не бэкенд."""

import asyncio
import threading
import time
from datetime import datetime

import pytest

from bridge.thread import BackendThread


class FakeBackend:
    """Ровно те методы, которые нужны проверкам границы потоков.

    Имена подобраны под свойства, а не под поверхность настоящего бэкенда:
    `together` держит `Event`, потому что «задачи идут разом, а не очередью»
    иначе не наблюдается — при очереди набор просто зависнет."""

    def __init__(self) -> None:
        self.closed = 0
        self.started = 0
        self.finished = 0
        self.running_at_close = None
        self.gate = asyncio.Event()

    async def echo(self, value):
        return value

    async def where(self):
        return asyncio.get_running_loop()

    async def moment(self):
        """Значение, которого `json.dumps` сам не переварит: им наблюдается, что
        перевод стоит на боевом пути, а не только зовётся тестом напрямую."""
        return datetime(2026, 7, 31, 12, 0)

    async def ident(self):
        return threading.get_ident()

    async def boom(self):
        raise RuntimeError("сломалось")

    async def slow(self):
        self.started += 1
        try:
            await asyncio.sleep(30)
        finally:
            self.finished += 1
        return "досидел"

    async def held(self):
        """Ждёт, пока её не отпустят: там, где важен порядок событий, сон не
        годится — он кончается сам."""
        self.started += 1
        try:
            await self.gate.wait()
        finally:
            self.finished += 1
        return "отпущен"

    async def release(self):
        self.gate.set()

    async def together(self, total):
        """Доходит только если все считаются разом."""
        self.started += 1
        if self.started >= total:
            self.gate.set()
        await self.gate.wait()
        return self.started

    async def aclose(self):
        # Сколько задач не доотменилось к этой секунде. Бэкенд, закрытый под
        # живой задачей, — это закрытый движок под открытой сессией, то есть
        # порядок закрытия наблюдаем только отсюда.
        self.running_at_close = self.started - self.finished
        self.closed += 1


async def ready(value):
    """Готовое значение корутиной: сборка бэкенда объявлена асинхронной."""
    return value


def wait_until(condition, timeout=5.0):
    """Ждать события в чужом потоке иначе нечем: своего цикла у теста нет."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(0.005)
    raise AssertionError("не дождались")


class Asked:
    """Записывающий фасад: имя собирается из точек, ответ берётся из словаря.

    Тест не пишет ни одного класса-двойника — весь бэкенд описывается словарём
    `{"tags.create": 7}`, а проверяется потом `log`: и имя, и аргументы, и
    порядок.

    Слабое место у приёма одно: принимается **любое** имя, и опечатка в имени
    метода бэкенда прошла бы молча. Закроет его отдельная проверка поверхности
    моста — она заводится вместе со сборкой моста, а пока имена сверены с
    настоящим бэкендом руками."""

    def __init__(self, answers: dict, log: list, path: tuple = ()) -> None:
        self._answers = answers
        self._log = log
        self._path = path

    def __getattr__(self, name):
        return Asked(self._answers, self._log, (*self._path, name))

    def __call__(self, *args, **kwargs):
        name = ".".join(self._path)
        self._log.append((name, args, kwargs))
        answer = self._answers.get(name)
        return _raising(answer) if isinstance(answer, Exception) else ready(answer)

    async def aclose(self):
        """Обычным методом, а не через `__getattr__`: иначе закрытие потока
        записалось бы в `log` и сбило проверки порядка."""


async def _raising(error):
    raise error


@pytest.fixture
def backend():
    return FakeBackend()


@pytest.fixture
def asked():
    """Пара «чем отвечать» и «о чём спросили»."""
    return {}, []


@pytest.fixture
def spy(asked):
    """Поток на записывающем двойнике: имена вызовов, доводы и номера заявок."""
    answers, log = asked
    yield from _running(Watched(lambda: ready(Asked(answers, log))))


class Watched(BackendThread):
    """Поток, который помнит номера заявок.

    Записывающий двойник бэкенда их не видит: номер уходит не в бэкенд, а в сам
    поток — им гасят устаревшее. Без этого подмена `op=op` на `op=None` в любом
    домене прошла бы молча, а лента стала бы неотменяемой."""

    def __init__(self, build) -> None:
        super().__init__(build)
        self.ops = []

    def run(self, factory, op=None):
        self.ops.append(op)
        return super().run(factory, op=op)


def _running(running):
    """Готовый поток, закрытый в любом случае: иначе повисший переживёт свой
    тест и утащит за собой соседний, а искать причину такого падения дороже,
    чем сам тест."""
    running.start()
    yield running
    running.close()


@pytest.fixture
def thread(backend):
    """Поток на двойнике поведения: счётчики, событие, сон."""
    yield from _running(BackendThread(lambda: ready(backend)))
