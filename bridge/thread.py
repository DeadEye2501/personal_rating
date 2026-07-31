"""Поток бэкенда: свой цикл asyncio, список живых задач, отмена всех разом."""

import asyncio
import concurrent.futures
import logging
import threading
from collections.abc import Callable, Coroutine
from typing import Any

logger = logging.getLogger(__name__)

# Сколько ждать сборки и закрытия. Сборка поднимает движок, открывает второй файл
# базы и заводит шесть клиентов сети — всё это диск и память, без единого запроса.
BUILD_TIMEOUT = 30.0

# Сколько ждать ответа. Сторож от невозвращающегося вызова, а не лимит на
# операцию: общего лимита у нас нет по решению. Самый долгий законный путь —
# карточка по ссылке в GOG, два запроса подряд по 20 секунд. Шестьдесят — выше
# любого законного с запасом и несравнимо ниже «навсегда».
#
# Объявлен здесь, а не у ждущего: ждёт того же самого потока и тот, кто отдаёт
# обложки, — а срок у ожидания один, из чего бы его ни ждали.
DEADLINE = 60.0


class Closed(Exception):
    """Поток закрыт, а его всё ещё о чём-то просят."""


class BackendThread:
    """Сборка внедряется, а не зовётся по имени, по двум причинам сразу:
    движок SQLAlchemy привязан к циклу, в котором создан, — значит бэкенд обязан
    родиться здесь, внутри; а импортировать `backend.app` из `bridge/` нельзя,
    с ним приедет `sqlalchemy` и покраснеет сторож границы слоёв."""

    def __init__(self, build: Callable[[], Coroutine[Any, Any, Any]]) -> None:
        self._build = build
        self._loop: asyncio.AbstractEventLoop | None = None
        self._backend: Any = None
        # Задача помнит свой ответ, а не просто себя: при закрытии обратные
        # вызовы уже не отработают, и разрешать ответы придётся отсюда.
        self._answers: dict[asyncio.Task, concurrent.futures.Future] = {}
        self._numbered: dict[int, asyncio.Task] = {}
        self._ready: concurrent.futures.Future = concurrent.futures.Future()
        self._thread = threading.Thread(target=self._live, name="backend",
                                        daemon=True)
        self._closed = False

    def start(self) -> None:
        """Ждём сборки здесь: не собрался бэкенд — окно поднимать незачем, и
        узнать об этом надо тем же исключением, а не тишиной."""
        self._thread.start()
        self._ready.result(timeout=BUILD_TIMEOUT)

    def run(self, factory: Callable[[Any], Coroutine],
            op: int | None = None) -> concurrent.futures.Future:
        """Заявка на работу. `factory` получает собранный бэкенд и отдаёт
        корутину — так мост не хранит ссылку на бэкенд у себя."""
        if self._closed:
            raise Closed("поток бэкенда закрыт")

        answer: concurrent.futures.Future = concurrent.futures.Future()
        self._loop.call_soon_threadsafe(self._begin, factory, op, answer)
        return answer

    def cancel(self, ops) -> None:
        """Неизвестный номер — обычное дело: ответ мог прийти раньше отмены.

        Тем же молчанием отвечает и отмена, обогнавшая саму заявку: та ещё едет
        к циклу и задачей не стала. Страницу это не задевает — её ответ всё
        равно отброшен по номеру, — но платит за это лишний поход в сеть.

        Закрытый поток тоже молчит: гасить там уже нечего, а разбудить его
        значит получить чужую ошибку в теле обработчика, откуда ей деться
        некуда."""
        if self._closed:
            return
        for op in ops:
            task = self._numbered.get(op)
            if task is not None:
                self._loop.call_soon_threadsafe(task.cancel)

    def close(self) -> None:
        """Закрыть могут дважды — окно при закрытии и фикстура теста."""
        if self._closed:
            return
        self._closed = True
        done: concurrent.futures.Future = concurrent.futures.Future()
        self._loop.call_soon_threadsafe(self._finish, done)
        done.result(timeout=BUILD_TIMEOUT)
        self._thread.join(timeout=BUILD_TIMEOUT)

    def _live(self) -> None:
        """Тело потока: цикл живёт ровно столько, сколько живёт бэкенд."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        try:
            self._backend = loop.run_until_complete(self._build())
        except Exception as error:
            # Сбой сборки — единственное, что уезжает вызывающему исключением:
            # без бэкенда окно поднимать незачем.
            logger.exception("бэкенд не собрался")
            self._refuse(error)
        else:
            self._ready.set_result(None)
            loop.run_forever()
        finally:
            if not self._ready.done():
                # Сборку оборвало не исключением, а `BaseException`. Не разбудив
                # ждущего, мы усадили бы его на весь `BUILD_TIMEOUT`.
                self._refuse(Closed("сборка оборвана"))
            loop.close()

    def _refuse(self, error: BaseException) -> None:
        """Цикла для заявок не будет, и знать об этом надо обоим: ждущему сборки
        — исключением, а `run` и `close` — закрытым состоянием, иначе они
        разбудят уже закрытый цикл и получат чужую ошибку вместо причины."""
        self._closed = True
        self._ready.set_exception(error)

    def _begin(self, factory, op, answer) -> None:
        """Уже в своём потоке: здесь можно заводить задачу."""
        if self._closed:
            # Заявка разминулась с закрытием: проверка в `run` идёт в чужом
            # потоке и от этого не спасает. Задача, заведённая после того, как
            # закрытие собрало живых, не дождётся никого — фьючерс не разрешился
            # бы никогда, и обработчик страницы повис бы навсегда.
            answer.set_exception(Closed("поток бэкенда закрыт"))
            return
        task = self._loop.create_task(factory(self._backend))
        self._answers[task] = answer
        if op is not None:
            self._numbered[op] = task
        task.add_done_callback(lambda ended: self._end(ended, op, answer))

    def _end(self, task, op, answer) -> None:
        self._answers.pop(task, None)
        if self._numbered.get(op) is task:
            # Номер мог достаться следующей заявке: у двухшаговой операции он тот
            # же самый. Снять чужую запись значит сделать её неотменяемой.
            del self._numbered[op]
        if task.cancelled():
            answer.cancel()
            answer.set_running_or_notify_cancel()
            return
        error = task.exception()
        if error is not None:
            answer.set_exception(error)
            return
        answer.set_result(task.result())

    def _finish(self, done) -> None:
        """Отмена всех разом, потом закрытие бэкенда, потом остановка цикла:
        порядок обратный сборке — сначала гасим то, что ещё ходит в сеть."""
        for task in list(self._answers):
            task.cancel()
        self._loop.create_task(self._shutdown(done))

    async def _shutdown(self, done) -> None:
        if self._answers:
            await asyncio.gather(*self._answers, return_exceptions=True)
        for answer in self._answers.values():
            # Обратный вызов задачи сюда уже не успевает: цикл остановится
            # раньше, чем он выполнится, и `loop.close()` его выбросит. Ответ,
            # оставшийся неразрешённым, повесил бы просителя навсегда.
            answer.cancel()
            answer.set_running_or_notify_cancel()
        try:
            await self._backend.aclose()
        except Exception:
            # Не закрылся начисто — окно всё равно обязано закрыться.
            logger.exception("бэкенд не закрылся начисто")
        finally:
            done.set_result(None)
            self._loop.stop()
