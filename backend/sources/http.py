"""Общая дверь в сеть для всех источников."""

import logging
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta

import httpx

from backend.sources.errors import Reason, Refusal

logger = logging.getLogger(__name__)

# Обязателен: без него запрос до MDBList не доходит — Cloudflare отвечает 403
# с телом «error code: 1010», не JSON.
USER_AGENT = "PersonalRating/0.1 (personal library app)"

DEFAULT_TIMEOUT = 20.0

# Пауза после сетевого отказа. Замерено: выключенный Wi-Fi отвечает ошибкой
# сразу, а сеть с пакетами в никуда досиживает весь таймаут — и так на каждой
# карточке прокрутки. Пятнадцать секунд, а не минуты: сеть возвращается сама.
NETWORK_BACKOFF = timedelta(seconds=15)


class Breaker:
    """Источник отказал по квоте — не ходим к нему до срока. Одна переменная
    в памяти вместо отметки о неудаче в сотнях строк базы."""

    def __init__(self, clock: Callable[[], datetime]) -> None:
        self._clock = clock
        self._until: datetime | None = None
        self._reason = Reason.QUOTA

    def is_open(self) -> bool:
        if self._until is None:
            return False
        if self._clock() >= self._until:
            self._until = None
            return False
        return True

    def trip(self, delay: timedelta, reason: Reason = Reason.QUOTA) -> None:
        """Причину запоминаем вместе со сроком. Взводят предохранитель и по
        квоте, и по частоте, а наружу все эти минуты уходит один и тот же
        отказ — человек увидит «кончилась суточная квота» там, где на деле
        «слишком часто, повтори через минуту»."""
        self._until = self._clock() + delay
        self._reason = reason

    @property
    def reason(self) -> Reason:
        return self._reason


class SourceHttp:
    """Классификацию ответов не делает: коды у шести источников разные, и
    разбирает их клиент источника."""

    def __init__(
        self,
        name: str,
        transport: httpx.AsyncBaseTransport | None = None,
        clock: Callable[[], datetime] = datetime.now,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.name = name
        # Часы держатся полем, а не только внутри предохранителя: у OMDB срок
        # отката считается до полуночи, и без общих часов его не проверить.
        self.clock = clock
        self.breaker = Breaker(clock)
        self._client = httpx.AsyncClient(
            transport=transport,
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        )

    async def get(
        self,
        url: str,
        params: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> httpx.Response | Refusal:
        if self.breaker.is_open():
            return Refusal(source=self.name, reason=self.breaker.reason,
                           detail="предохранитель взведён")
        try:
            return await self._client.get(url, params=params, headers=headers)
        except httpx.HTTPError as error:
            logger.warning("%s: сеть — %s", self.name, error)
            # Пустая сеть — беда не этого запроса, а всех следующих.
            self.breaker.trip(NETWORK_BACKOFF, Reason.NETWORK)
            return Refusal(source=self.name, reason=Reason.NETWORK,
                           detail=str(error))

    async def aclose(self) -> None:
        await self._client.aclose()
