"""Один формат ответа на все операции: `{"ok": ...}` либо `{"fail": ...}`."""

import logging
import threading

from backend.model import TagExists
from bridge.answer import Domain, kebab
from tests.bridge.conftest import wait_until


class Probe(Domain):
    """Домен из одного метода: проверяется оболочка, а не чей-то предмет."""

    def ask(self, what, op=None):
        return self._reply(lambda back: getattr(back, what)(), op=op)


def test_a_result_comes_wrapped(thread):
    assert Probe(thread).ask("ident")["ok"] > 0


def test_the_answer_is_translated_on_the_way_out(thread):
    """Перевод стоит на единственном боевом пути. Без него `datetime` уедет в
    `json.dumps` внутри pywebview, и страница получит отклонённый промис на весь
    ответ, а не пустое поле."""
    assert Probe(thread).ask("moment") == {"ok": "2026-07-31T12:00:00"}


def test_a_denial_becomes_a_kind_of_failure(thread, backend):
    """Ловим одного предка, а род берём по имени класса: седьмой отказ иначе
    пришлось бы дописывать и в бэкенд, и сюда."""
    async def taken():
        raise TagExists("драма")

    backend.taken = taken
    assert Probe(thread).ask("taken") == {"fail": "tag-exists",
                                          "detail": "драма"}


def test_the_unexpected_becomes_broken_and_is_logged(thread, caplog):
    """Молча не глотаем: непредвиденное даёт и плашку, и запись с трассировкой."""
    with caplog.at_level(logging.ERROR):
        answer = Probe(thread).ask("boom")

    assert answer["fail"] == "broken"
    assert any(record.exc_info for record in caplog.records)


def test_a_timeout_raised_by_the_operation_is_not_ours(thread, backend, caplog):
    """`concurrent.futures.TimeoutError` — это встроенный `TimeoutError`, и
    такой же вправе поднять сама операция. Выдав её за наш срок, мы отдали бы
    странице «не дождались», соврали бы в логе и не записали бы трассировку —
    то есть потеряли бы настоящую ошибку целиком."""
    async def impatient():
        raise TimeoutError("чужой срок")

    backend.impatient = impatient
    with caplog.at_level(logging.ERROR):
        answer = Probe(thread).ask("impatient")

    assert answer == {"fail": "broken", "detail": "чужой срок"}
    assert any(record.exc_info for record in caplog.records)


def test_a_cancelled_operation_answers_quietly(thread, backend):
    """Отменённая молчит: плашки за уход со страницы не бывает."""
    answer = {}
    caller = threading.Thread(
        target=lambda: answer.update(value=Probe(thread).ask("slow", op=1)))
    caller.start()
    wait_until(lambda: backend.started == 1)

    thread.cancel([1])
    caller.join(timeout=5)

    assert answer["value"] == {"fail": "cancelled"}


def test_a_hung_call_is_cut_off(thread, backend, monkeypatch):
    """У pywebview срока нет вовсе: зависший вызов оставил бы вечный промис."""
    monkeypatch.setattr("bridge.answer.DEADLINE", 0.05)

    assert Probe(thread).ask("slow", op=2) == {"fail": "timeout"}
    # Срок не только отвечает, но и гасит работу: иначе она досидит все тридцать
    # секунд, тратя квоту источника на ответ, которого никто не ждёт.
    wait_until(lambda: backend.finished == 1)


def test_a_hung_call_without_a_number_answers_too(thread, backend, monkeypatch):
    """Без номера ходят четыре домена из семи: записи оценок, тегов, закладок и
    правки карточки. Гасить там нечего — работа остаётся жить, — но ответ обязан
    прийти, иначе промис страницы висел бы вечно именно на записи."""
    monkeypatch.setattr("bridge.answer.DEADLINE", 0.05)

    assert Probe(thread).ask("slow") == {"fail": "timeout"}
    assert backend.finished == 0


def test_a_closed_thread_answers_instead_of_raising(thread):
    """Окно закрыли, а поздний обработчик страницы всё ещё что-то просит."""
    thread.close()
    assert Probe(thread).ask("ident") == {"fail": "closed"}


def test_the_kind_of_failure_is_kebab():
    assert kebab("TagExists") == "tag-exists"
    assert kebab("ExternalIdTaken") == "external-id-taken"
    assert kebab("BadImage") == "bad-image"
