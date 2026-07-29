"""Операторы над таблицами, которые в проекте собираются одинаково."""

from sqlalchemy import Column, Delete, Table, delete
from sqlalchemy.dialects.sqlite import Insert, insert


def clearing(table: Table, item_id: int) -> Delete:
    """Снести всё, что в этой таблице числится за карточкой.

    Оператор возвращается, а не выполняется: замена набора жанров кладёт его в
    одну транзакцию со вставкой, и половина такой замены хуже, чем ничего."""
    return delete(table).where(table.c.item_id == item_id)


def upserting(table: Table, values: dict, key: list[Column]) -> Insert:
    """Вставка, которая на занятом ключе обновляет всё остальное.

    Оператор возвращается, а не выполняется: одному вызывающему занятый ключ
    уникальности — повод для своего исключения, другому — обычное дело.
    Обновляется всё переданное, кроме самого ключа: его перезапись сменила бы
    строке личность."""
    statement = insert(table).values(**values)
    keyed = {column.name for column in key}
    return statement.on_conflict_do_update(
        index_elements=key,
        set_={name: statement.excluded[name]
              for name in values if name not in keyed},
    )
