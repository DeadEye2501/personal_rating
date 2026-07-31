"""Разговор с магазином, который своих лимитов не объявляет."""

from datetime import timedelta

import httpx

from backend.model import Reason, Refusal
from backend.sources.backoff import refuse_until
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
        return refuse_until(http, Reason.RATE, UNDOCUMENTED_BACKOFF)
    return refuse_code(http.name, status)


async def asked(http: SourceHttp, url: str,
                params: dict | None = None) -> httpx.Response | Refusal:
    """Ответ, годный к разбору, — либо отказ, который уже всё решил.

    Одинаково у обоих магазинов и у всех трёх их запросов: отказ на обрыв и
    на взведённый предохранитель собирает транспорт, а любой код кроме 200 ни
    Steam, ни GOG не описывают нигде.

    Товарной ручки GOG это не касается: её 404 означает «такого продукта нет» и
    перехватывается раньше, до `refuse_undocumented`."""
    response = await http.get(url, params=params)
    if not isinstance(response, httpx.Response):
        return response
    if response.status_code != 200:
        return refuse_undocumented(http, response.status_code)
    return response
