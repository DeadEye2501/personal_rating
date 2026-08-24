"""Приведение хранимых оценок к настроенной шкале.

Живёт в `storage/`, а не в `service/`: предмет здесь — содержимое одной таблицы
и отметка в заголовке файла базы, и ни одного решения о том, что показывать.

Зовётся из сборки, потому что там движок: пересчёт обязан случиться до первого
запроса, а сборка — единственное место, где база уже открыта, а спросить её ещё
никто не успел.
"""

import logging

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.config import TEN
from backend.model import ASPECTS, average_score
from backend.storage.tables import rating

logger = logging.getLogger(__name__)


def rescaled(value: float | None, scale: int) -> int | None:
    """Оценка в новой шкале.

    Вниз — округлением вверх: девятка и десятка обе становятся пятёркой, так
    решил пользователь. Вверх — умножением на два, и нечётные значения после
    круга туда-обратно не восстанавливаются.
    """
    if value is None:
        return None
    whole = int(value)
    return whole * 2 if scale == TEN else (whole + 1) // 2


async def apply_scale(sessions: async_sessionmaker[AsyncSession],
                      scale: int) -> None:
    """Привести оценки к шкале из настроек, если она сменилась.

    Сравнивать `.env` не с чем: база про свою шкалу не знает, а вывести шкалу из
    данных нельзя — библиотека из одних троек выглядит одинаково в обеих.
    Поэтому шкала базе и записывается.
    """
    async with sessions() as session:
        # Ноль — это база, заведённая до появления настройки: шкала в ней
        # десятибалльная. Прими мы ноль за «неизвестно», первый же запуск новой
        # версии удвоил бы всю библиотеку.
        stored = (await session.execute(
            text("PRAGMA user_version"))).scalar_one() or TEN
        if stored == scale:
            return

        for row in (await session.execute(select(rating))).all():
            await session.execute(
                update(rating).where(rating.c.item_id == row.item_id)
                .values(**_moved(row, scale)))
        # Подстановкой, а не параметром: PRAGMA связанных значений не принимает.
        # Число сюда приходит из настроек и бывает ровно двух видов.
        #
        # Той же транзакцией, что и оценки: замерено, что `user_version`
        # откатывается вместе с ней, — иначе оборванный пересчёт оставил бы
        # половину библиотеки под отметкой, обещающей всю.
        await session.execute(text(f"PRAGMA user_version = {scale}"))
        await session.commit()
    logger.info("оценки переведены на шкалу из %s ступеней", scale)


def _moved(row, scale: int) -> dict:
    """Три стороны игры и оценка.

    Средняя игры собирается из пересчитанных сторон: пересчитанная сама, она
    разошлась бы со сторонами, показанными рядом в той же карточке."""
    sides = {name: rescaled(getattr(row, name), scale) for name in ASPECTS}
    average = average_score(*sides.values())
    return {**sides,
            "score": average if average is not None
            else rescaled(row.score, scale)}
