"""Чем может кончиться запрос к источнику: находкой, честным «нет» или отказом."""

from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum
from typing import TypeAlias


class Reason(StrEnum):
    QUOTA = "quota"       # кончилась суточная квота
    RATE = "rate"         # слишком часто, либо «повтори позже»
    KEY = "key"           # ключа нет, битый или отозван
    NETWORK = "network"   # не дозвонились, либо нас не пустил чужой периметр
    BROKEN = "broken"     # ответил, но непонятно чем


@dataclass(frozen=True, slots=True)
class Found[T]:
    value: T


@dataclass(frozen=True, slots=True)
class Missing:
    """Источник ответил, и такого у него нет. Это ответ, а не молчание:
    он пишется в базу пустым значением и живёт неделю."""


@dataclass(frozen=True, slots=True)
class Refusal:
    """Отказ в обслуживании. В базу не пишется вовсе — спросим при следующем
    показе."""

    source: str
    reason: Reason
    retry_after: timedelta | None = None
    detail: str = ""


Outcome: TypeAlias = Found | Missing | Refusal


def is_answer(outcome: Outcome) -> bool:
    """Источник ответил: нашёл или честно сказал, что не знает. Отказ ответом не
    считается никогда, а можно ли записать ответ — решает пишущий: у поиска GOG,
    например, «не нашлось» неотличимо от «поиск не справился»."""
    return isinstance(outcome, (Found, Missing))
