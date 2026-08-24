"""Общая дверь в сеть для всех источников."""

import asyncio
import logging
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta

import httpx

from backend.model import Reason, Refusal, Source

logger = logging.getLogger(__name__)

# Обязателен: без него запрос до MDBList не доходит — Cloudflare отвечает 403
# с телом «error code: 1010», не JSON.
#
# Контакт в скобках — не вежливость: часть сайтов отказывает без него прямо.
# Замерено 03.08.2026 — Wikimedia отвечает `403` и текстом «Please respect our
# robot policy… Contact bot-traffic@wikimedia.org». Адрес личный и уезжает в
# каждый запрос к каждому источнику; поставлен решением пользователя.
USER_AGENT = "PersonalRating/0.1 (dead.eye.2501@gmail.com)"

DEFAULT_TIMEOUT = 20.0

# Пауза после сетевого отказа. Замерено: выключенный Wi-Fi отвечает ошибкой
# сразу, а сеть с пакетами в никуда досиживает весь таймаут — и так на каждой
# карточке прокрутки. Пятнадцать секунд, а не минуты: сеть возвращается сама.
NETWORK_BACKOFF = timedelta(seconds=15)

# Сколько запросов к источнику держать в полёте. Названы только те, кому предел
# нужен: Steam и GOG держат двадцать разом без единого отказа, и тормозить их
# незачем. FantLab тоже не назван, и это замер, а не недосмотр: числа его волны
# записаны там, где она и уходит, — `service/search.py:_covered`.
#
# У old-games.ru замерено обратное: волной по двадцать выходит восемь успешных и
# двенадцать `503`, очередью по четыре — двадцать из двадцати и ни одного, причём
# за то же время. Узкое место в самом сервере, около двух карточек в секунду, так
# что вежливость здесь бесплатна.
#
# Предел стоит здесь, а не в клиенте, потому что соединений к этому сайту два:
# карточки идут своим, обложки — своим, `<имя>-poster`. Ограничитель в клиенте
# постерный путь не накрывал вовсе.
# Ключ — значение перечисления, а не литерал: постерное имя собирается в
# сборке как `f"{source}-poster"`, и с литералом переименование источника
# молча уносило бы очередь у обложек, оставляя её у карточек.
AT_ONCE = {Source.OLD_GAMES: 4}


# Хвост имени постерного соединения. Одной строкой на оба места — и на сборку
# имени, и на его разбор: разойдись они, предел молча перестал бы накрывать
# обложки, а сторож остался бы зелёным.
POSTER_SUFFIX = "-poster"


def poster_name(source: str) -> str:
    """Имя соединения, которым ходят за обложками этого источника.

    Довод здесь строкой, а не `Source`: у заимодавца обложек своего значения
    там нет — почему, сказано у `PosterService.__init__`, где ключи и
    приводятся."""
    return f"{source}{POSTER_SUFFIX}"


def _limit(name: str) -> int | None:
    """Предел для этого соединения. У карточек и обложек он общий: сервер-то
    один."""
    return AT_ONCE.get(name.removesuffix(POSTER_SUFFIX))


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
        limit = _limit(name)
        self._turn = asyncio.Semaphore(limit) if limit else None
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
        return await self._asked("GET", url, params, headers)

    async def head(
        self,
        url: str,
        params: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> httpx.Response | Refusal:
        """Есть ли что по этому адресу и что именно — без самой картинки.

        Заведено на обложках FantLab: у крупного размера бывает 404 — три
        издания из тринадцати, замерено 23.08.2026, — а качать 350 КБ ради
        проверки незачем. Предохранитель, очередь и разбор отказа общие с
        `get`: для них способ запроса не значит ничего."""
        return await self._asked("HEAD", url, params, headers)

    async def _asked(
        self,
        way: str,
        url: str,
        params: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> httpx.Response | Refusal:
        if self.breaker.is_open():
            return Refusal(source=self.name, reason=self.breaker.reason,
                           detail="предохранитель взведён")
        if self._turn is None:
            return await self._fetched(way, url, params, headers)
        async with self._turn:
            return await self._fetched(way, url, params, headers)

    async def _fetched(
        self,
        way: str,
        url: str,
        params: Mapping[str, object] | None,
        headers: Mapping[str, str] | None,
    ) -> httpx.Response | Refusal:
        try:
            return await self._client.request(way, url, params=params,
                                              headers=headers)
        except httpx.HTTPError as error:
            logger.warning("%s: сеть — %s", self.name, error)
            # Пустая сеть — беда не этого запроса, а всех следующих.
            self.breaker.trip(NETWORK_BACKOFF, Reason.NETWORK)
            return Refusal(source=self.name, reason=Reason.NETWORK,
                           detail=str(error))

    async def aclose(self) -> None:
        await self._client.aclose()
