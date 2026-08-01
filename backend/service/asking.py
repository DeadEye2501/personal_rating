"""Запрос к источнику, из которого не вылетает исключение."""

import asyncio
import logging
from collections.abc import Iterable

from backend.sources.errors import broken

logger = logging.getLogger(__name__)


async def answered(awaitable, source: str):
    """Исход запроса, что бы ни случилось.

    Клиенты ловят только то, чем падает провод и разбор; всё остальное — чужая
    библиотека, наша опечатка — вылетело бы из сервиса наружу, а у границы
    потоков второго канала доставки нет. Отказ вместо срыва.

    Отмена не ловится: она наследник `BaseException`, и гасят ею нас, а не
    источник. Превратить её в отказ значит соврать про закрытие приложения."""
    try:
        return await awaitable
    except Exception as error:
        logger.exception("%s: запрос сорвался", source)
        return broken(source, error)


async def answered_all(requests: Iterable[tuple]) -> list:
    """Несколько запросов разом, и ни один не вылетает исключением.

    Пары «корутина и имя источника», а не клиенты с методом: спрашивают этим
    трое, и спрашивают разное — выдачу магазинов, фильмографии тёзок, чужие
    оценки. Общее у них не запрос, а правило: мимо `answered` к источнику не
    ходит никто, и держаться оно должно не перепиской руками — забытая обёртка
    в четвёртой копии оставила бы набор зелёным, а исключение ушло бы через
    границу потоков."""
    return await asyncio.gather(
        *(answered(awaitable, source) for awaitable, source in requests)
    )
