"""Запрос к источнику, из которого не вылетает исключение."""

import logging

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
