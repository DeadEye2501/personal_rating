"""Граница потоков: что обязано быть правдой у стыка двух циклов."""

import asyncio
import concurrent.futures
import threading

import pytest

from bridge.thread import BackendThread, Closed
from tests.bridge.conftest import FakeBackend, ready, wait_until


def test_work_runs_in_another_thread(thread):
    """Главное свойство: в потоке интерфейса не выполняется ничего бэкендового."""
    other = thread.run(lambda back: back.ident()).result(timeout=5)
    assert other != threading.get_ident()


def test_the_answer_comes_back(thread):
    assert thread.run(lambda back: back.echo(7)).result(timeout=5) == 7


def test_the_backend_is_built_inside_that_thread(backend):
    """Движок SQLAlchemy привязан к циклу, в котором создан, — значит и сборка
    обязана идти внутри, а не снаружи с передачей готового."""
    seen = {}

    async def build():
        seen["thread"] = threading.get_ident()
        seen["loop"] = asyncio.get_running_loop()
        return backend

    running = BackendThread(build)
    running.start()
    try:
        assert seen["thread"] != threading.get_ident()
        assert running.run(lambda back: back.where()).result(timeout=5) is seen["loop"]
    finally:
        running.close()


def test_a_broken_build_reaches_the_caller(caplog):
    """Не собрался бэкенд — об этом узнают снаружи, а не по тишине в окне.
    Причина при этом остаётся и в логе: наружу уезжает исключение сборки, а чем
    именно она сорвалась, дочитывают там."""
    async def build():
        raise RuntimeError("нет ключа")

    running = BackendThread(build)
    with pytest.raises(RuntimeError, match="нет ключа"):
        running.start()

    assert "бэкенд не собрался" in caplog.text


def test_closing_after_a_broken_build_is_quiet():
    """Окно обернёт `start()` в `try/finally`, и вторичная ошибка закрытия
    затёрла бы настоящую причину — «нет ключа»."""
    async def build():
        raise RuntimeError("нет ключа")

    running = BackendThread(build)
    with pytest.raises(RuntimeError, match="нет ключа"):
        running.start()

    running.close()
    with pytest.raises(Closed):
        running.run(lambda back: back.echo(1))


def test_a_broken_task_does_not_kill_the_thread(thread):
    with pytest.raises(RuntimeError, match="сломалось"):
        thread.run(lambda back: back.boom()).result(timeout=5)

    assert thread.run(lambda back: back.echo("живой")).result(timeout=5) == "живой"


def test_a_cancelled_task_is_really_stopped(thread, backend):
    """Отменяется задача, а не заявка: `CancelledError` обязан прийти внутрь
    бэкенда, иначе откатывать сорванную запись будет нечему."""
    future = thread.run(lambda back: back.slow(), op=1)
    wait_until(lambda: backend.started == 1)

    thread.cancel([1])

    with pytest.raises(concurrent.futures.CancelledError):
        future.result(timeout=5)
    wait_until(lambda: backend.finished == 1)


def test_cancelling_takes_a_list(thread, backend):
    """Страница уходит целиком, и её задачи гасятся одним пересечением границы,
    а не восемнадцатью."""
    futures = [thread.run(lambda back: back.slow(), op=number)
               for number in (1, 2, 3)]
    wait_until(lambda: backend.started == 3)

    thread.cancel([1, 2, 3])

    for future in futures:
        with pytest.raises(concurrent.futures.CancelledError):
            future.result(timeout=5)


def test_cancelling_touches_only_the_named_ones(thread, backend):
    """Гасится названное, а не всё живое: рядом с отменяемым поиском в том же
    потоке идут записи, которые отменять нельзя ни при каких обстоятельствах."""
    doomed = thread.run(lambda back: back.slow(), op=1)
    spared = thread.run(lambda back: back.slow(), op=2)
    wait_until(lambda: backend.started == 2)

    thread.cancel([1])

    with pytest.raises(concurrent.futures.CancelledError):
        doomed.result(timeout=5)
    wait_until(lambda: backend.finished == 1)
    assert not spared.done()


def test_the_number_taken_twice_stays_cancellable(thread, backend):
    """Второй шаг двухшаговой операции зовётся тем же номером — это решение
    проекта. Первый шаг, доигравший позже, не вправе унести с собой запись,
    которая принадлежит уже второму."""
    first = thread.run(lambda back: back.held(), op=7)
    second = thread.run(lambda back: back.slow(), op=7)
    wait_until(lambda: backend.started == 2)

    thread.run(lambda back: back.release()).result(timeout=5)
    assert first.result(timeout=5) == "отпущен"

    thread.cancel([7])

    with pytest.raises(concurrent.futures.CancelledError):
        second.result(timeout=5)


def test_cancelling_an_unknown_number_is_quiet(thread):
    """Ответ пришёл раньше, чем страница успела отменить, — это обычное дело."""
    thread.cancel([404])


def test_tasks_run_together_not_in_a_queue(thread):
    """Пять доходят, только если считаются разом: при очереди набор зависнет на
    первой, которая ждёт остальных."""
    futures = [thread.run(lambda back: back.together(5)) for _ in range(5)]
    for future in futures:
        assert future.result(timeout=5) == 5


def test_closing_cancels_instead_of_waiting_them_out(thread, backend):
    """Гасим, а не досиживаем: иначе закрытие окна ждало бы каждого висящего
    запроса до срока источника. Вторая заявка идёт без номера — по решению
    проекта таких большинство: оценки, теги и закладки номера не несут.

    Утверждения после `close()` идут без ожидания нарочно: `close()` обязан
    вернуться только тогда, когда всё это уже правда."""
    numbered = thread.run(lambda back: back.slow(), op=1)
    plain = thread.run(lambda back: back.slow())
    wait_until(lambda: backend.started == 2)

    thread.close()

    for future in (numbered, plain):
        with pytest.raises(concurrent.futures.CancelledError):
            future.result(timeout=5)
    assert backend.finished == 2
    assert backend.closed == 1
    assert backend.running_at_close == 0


def test_closing_waits_for_the_cancelled_before_closing_the_backend(backend):
    """Уборка сорванной записи у настоящего бэкенда — это `await`, а не
    инструкция: он ловит отмену и откатывает карточку. Закрой движок вперёд
    отката — и в базе останется строка без жанров и состава, но со свежим
    `synced_at`, то есть карточка, которая никогда не перезапросится.

    Двойник для этого нужен свой: у обычного `slow` уборка доигрывает на первом
    же пробуждении, и порядок закрытия на нём не наблюдается вовсе."""
    class Unwinding(FakeBackend):
        async def slow(self):
            self.started += 1
            try:
                await asyncio.sleep(30)
            finally:
                await asyncio.sleep(0)
                await asyncio.sleep(0)
                self.finished += 1

    unwinding = Unwinding()
    running = BackendThread(lambda: ready(unwinding))
    running.start()
    running.run(lambda back: back.slow())
    wait_until(lambda: unwinding.started == 1)

    running.close()

    assert unwinding.running_at_close == 0


def test_a_request_that_raced_closing_is_refused(thread):
    """Проверка в `run` идёт в чужом потоке и от гонки не спасает. Заявка,
    попавшая между сбором живых и остановкой цикла, заводит задачу, которой уже
    никто не дождётся, — и промис страницы висит навсегда."""
    thread.close()
    answer: concurrent.futures.Future = concurrent.futures.Future()

    thread._begin(lambda back: back.echo(1), None, answer)

    with pytest.raises(Closed):
        answer.result(timeout=1)


def test_cancelling_after_closing_is_quiet(thread):
    """Окно закрывают, пока лента гасит свои порции. Разбуженный закрытый цикл
    поднял бы ошибку прямо в теле обработчика страницы, откуда ей деться
    некуда."""
    thread.close()

    thread.cancel([1, 2])


def test_closing_ends_the_thread(thread):
    """Иначе окно закрывается на процессе, у которого крутится чужой цикл, — а
    держится это одним лишь флагом `daemon`."""
    thread.close()

    wait_until(lambda: all(alive.name != "backend"
                           for alive in threading.enumerate()))


def test_closing_twice_is_quiet(thread):
    thread.close()
    thread.close()


def test_a_call_after_closing_is_refused_not_hung(thread):
    """Окно закрыли, а поздний обработчик страницы всё ещё что-то просит."""
    thread.close()
    with pytest.raises(Closed):
        thread.run(lambda back: back.echo(1))


def test_the_thread_survives_a_backend_that_will_not_close():
    """Закрытие обязано доходить до конца даже так: иначе окно не закроется."""
    class Stubborn(FakeBackend):
        async def aclose(self):
            raise RuntimeError("не закрылся")

    running = BackendThread(lambda: ready(Stubborn()))
    running.start()
    running.close()


# Оборванная сборка обязана уронить поток — это и проверяется. pytest считает
# улетевшее из чужого потока исключение поводом для предупреждения и вешает его
# на случайного соседа; здесь оно и есть ожидаемое поведение, а не находка.
@pytest.mark.filterwarnings(
    "ignore::pytest.PytestUnhandledThreadExceptionWarning")
def test_a_build_torn_off_by_something_worse_still_wakes_the_caller():
    """Сборку может оборвать не только `Exception`. Не разбудив ждущего, мы
    усадили бы его на весь срок сборки и не сказали бы ни слова о причине —
    тот же класс, что однажды дала отмена посреди записи карточки."""
    async def build():
        raise KeyboardInterrupt

    running = BackendThread(build)

    with pytest.raises(Closed):
        running.start()

    # Дожидаемся конца потока здесь: иначе его падение всплывёт уже в чужом
    # тесте, и жалоба повиснет на невиновном соседе.
    wait_until(lambda: all(alive.name != "backend"
                           for alive in threading.enumerate()))
