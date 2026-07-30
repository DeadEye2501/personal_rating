"""Как источник сообщает, что ответ не разобрался."""

from collections.abc import Callable
from logging import Logger

from backend.model import Reason, Refusal

# Чем падает разбор чужого ответа. Не только `ValueError`: на словаре вместо
# списка приезжает `TypeError`, на отсутствующем ключе — `KeyError`, на `None`
# вместо тела — `AttributeError`.
BROKEN_BY_PARSING = (ValueError, TypeError, KeyError, AttributeError)


def broken(source: str, error: Exception) -> Refusal:
    """Отказ по неразобранному ответу. Запись в лог остаётся на месте вызова:
    сообщение у каждого своё, и по нему потом ищут причину."""
    return Refusal(source=source, reason=Reason.BROKEN, detail=str(error))


def parsed[T](log: Logger, source: str, note: str,
              produce: Callable[[], T]) -> T | Refusal:
    """Разбор чужого ответа: получилось — отдаём как есть, сорвалось — записываем
    и отказываем.

    Заведено на девяти копиях одного и того же `try/except` в шести клиентах:
    седьмой источник, написанный по образцу, легко получил бы `except Exception`
    вместо перечня или `Refusal` вместо `broken`, и заметить это было бы негде.

    `log` передаётся, а не берётся здесь: запись должна называть модуль
    источника, иначе в логе шесть клиентов выглядят одним. `note` — готовая
    фраза, а не подстановка: у клиента таких мест до трёх, и различает их только
    она."""
    try:
        return produce()
    except BROKEN_BY_PARSING as error:
        log.warning("%s: %s — %s", source, note, error)
        return broken(source, error)
