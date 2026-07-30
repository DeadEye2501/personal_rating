"""Отказ источника, который своих лимитов не объявляет."""

from datetime import timedelta

from backend.model import Reason, Refusal
from backend.sources.errors import refuse_code
from backend.sources.http import SourceHttp

# Ни Steam, ни GOG лимитов не объявляют: у Steam 220 запросов подряд прошли без
# троттлинга, у GOG документации нет вовсе. Пять минут — догадка, но лучше, чем
# долбиться в закрытую дверь.
UNDOCUMENTED_BACKOFF = timedelta(minutes=5)


def refuse_undocumented(http: SourceHttp, status: int) -> Refusal:
    """Отдельным модулем, а не методом `SourceHttp`: транспорт ответы не
    классифицирует, коды у шести источников разные."""
    if status == 429:
        http.breaker.trip(UNDOCUMENTED_BACKOFF, Reason.RATE)
        return Refusal(
            source=http.name, reason=Reason.RATE, retry_after=UNDOCUMENTED_BACKOFF
        )
    return refuse_code(http.name, status)
