"""Оболочка вызова моста: срок, отказ, один формат ответа.

Наружу уходит либо `{"ok": <значение>}`, либо `{"fail": <род>, "detail": ...}`.
Третьего вида нет, и исключений наружу не летит: у границы потоков второго
канала доставки не бывает."""

import concurrent.futures
import logging
import re

from backend.model import Denied
from bridge.thread import DEADLINE, Closed
from bridge.wire import to_wire

logger = logging.getLogger(__name__)

_EDGE = re.compile(r"(?<!^)(?=[A-Z])")


def kebab(name: str) -> str:
    """`TagExists` → `tag-exists`. Род отказа берётся из имени класса, а не из
    таблицы: таблица разошлась бы с моделью молча."""
    return _EDGE.sub("-", name).lower()


class Domain:
    """Общее у семи доменов моста.

    Имена с подчёркиванием pywebview на страницу не выносит — поверхностью
    становятся только методы наследников."""

    def __init__(self, thread) -> None:
        self._thread = thread

    def _reply(self, factory, op: int | None = None) -> dict:
        try:
            answer = self._thread.run(factory, op=op)
            try:
                value = answer.result(timeout=DEADLINE)
            except TimeoutError:
                # `concurrent.futures.TimeoutError` — это встроенный
                # `TimeoutError`, и такой же вправе поднять сама операция.
                # Различает их не тип, а то, ответила ли она: наш срок истекает
                # на неотвеченной. Чужой уходит в общий улов, вместе с
                # трассировкой, — иначе настоящая ошибка пропала бы целиком.
                if answer.done():
                    raise
                # Срок не только отвечает, но и гасит работу: иначе она досидит
                # своё, тратя квоту источника на ответ, которого уже никто не
                # ждёт. Гасится названное номером; без номера гасить нечего, и
                # такая работа доживает свой век сама.
                self._thread.cancel([op])
                logger.error("операция не уложилась в %s с", DEADLINE)
                return {"fail": "timeout"}
            return {"ok": to_wire(value)}
        except Closed:
            return {"fail": "closed"}
        except concurrent.futures.CancelledError:
            return {"fail": "cancelled"}
        except Denied as denial:
            return {"fail": kebab(type(denial).__name__), "detail": str(denial)}
        except Exception as error:
            logger.exception("непредвиденный сбой операции")
            return {"fail": "broken", "detail": str(error)}
