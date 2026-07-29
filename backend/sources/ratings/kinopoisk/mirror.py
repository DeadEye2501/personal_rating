"""Общее у двух зеркал Кинопоиска."""

from datetime import timedelta

from backend.model import Ratings
from backend.sources.errors import Found, Missing, Outcome, Reason, Refusal
from backend.sources.http import SourceHttp

# Наружу зеркала неразличимы: оба отдают один идентификатор и одну оценку, и в
# данных не отражается, какое из них ответило.
SOURCE = "kinopoisk"

# Квота суточная и самая жёсткая из всех источников: 500 запросов. Ждать до
# полуночи, как у OMDB, нельзя — зеркала считают сутки по-своему и об этом не
# сообщают.
QUOTA_BACKOFF = timedelta(hours=6)

# На запасном зеркале ограничение — пять запросов в секунду; у основного
# частотного ответа в документации нет вовсе, но он приходит.
RATE_BACKOFF = timedelta(minutes=1)


def refuse_quota(http: SourceHttp) -> Refusal:
    http.breaker.trip(QUOTA_BACKOFF)
    return Refusal(source=SOURCE, reason=Reason.QUOTA, retry_after=QUOTA_BACKOFF)


def refuse_rate(http: SourceHttp) -> Refusal:
    """Предохранитель здесь обязателен: без него `KinopoiskClient` на каждый
    частотный ответ дёргал бы второе зеркало, тратя его суточные пятьсот."""
    http.breaker.trip(RATE_BACKOFF, Reason.RATE)
    return Refusal(source=SOURCE, reason=Reason.RATE, retry_after=RATE_BACKOFF)


def refuse_key() -> Refusal:
    """Предохранитель не взводится: битый ключ сроком не лечится."""
    return Refusal(source=SOURCE, reason=Reason.KEY)


def refuse_code(status: int) -> Refusal:
    return Refusal(source=SOURCE, reason=Reason.BROKEN, detail=f"HTTP {status}")


def answered(answer: Ratings) -> Outcome:
    """Пусто целиком — «такого у нас нет». Фильм найден, а оценки у него нет —
    это находка с пустыми значениями: иначе вместе с `Missing` улетел бы
    добытый идентификатор Кинопоиска, ради которого мы сюда и ходим."""
    if not answer.values and not answer.external_ids:
        return Missing()
    return Found(answer)
