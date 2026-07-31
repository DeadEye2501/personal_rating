"""Значения границы в то, что переживёт `json.dumps`.

Своего кодировщика у pywebview нет: результат уходит в `json.dumps` без
`default=`, поэтому перевести всё надо до возврата."""

import dataclasses
import math
from datetime import date, datetime, timedelta
from enum import Enum

from backend.model import Missing, Refusal


def to_wire(value):
    """Отказ громкий, а не `default=str`: неизвестный тип, подставленный
    строкой, доедет до страницы и сломается там, где искать его будет некому.

    Порядок ветвей значащий: `Enum` идёт первым, потому что наши перечисления
    наследуют `str` — проверка на примитив забрала бы их себе и отдала наружу
    объектом перечисления, а не строкой."""
    if isinstance(value, Enum):
        return value.value
    if value is None or isinstance(value, int | str):
        return value
    if isinstance(value, float):
        # `json.dumps` печатает `NaN` и `Infinity`, а `JSON.parse` их не берёт:
        # упало бы разбором всего ответа, а не одного поля.
        return None if math.isnan(value) or math.isinf(value) else value
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, timedelta):
        return value.total_seconds()
    if isinstance(value, bytes | bytearray):
        raise TypeError("байты через мост не ходят: обложка едет ручкой")
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {field.name: to_wire(getattr(value, field.name))
                for field in dataclasses.fields(value)}
    if isinstance(value, list | tuple):
        return [to_wire(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_wire(item) for key, item in value.items()}
    raise TypeError(f"через мост не проходит: {type(value).__name__}")


def outcome(value) -> dict:
    """Одна форма на три исхода запроса к источнику.

    `Missing` — датакласс без единого поля, и после разбора это `{}`,
    неотличимое от чего угодно пустого. Различать по набору ключей нельзя,
    поэтому метку приклеиваем здесь."""
    if isinstance(value, Missing):
        return {"outcome": "missing"}
    if isinstance(value, Refusal):
        return {"outcome": "refusal", "refusal": to_wire(value)}
    return {"outcome": "found", "value": to_wire(value)}
