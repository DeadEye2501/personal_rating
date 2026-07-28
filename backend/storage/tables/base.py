"""Общее для всех объявлений схемы."""

from typing import Any

from sqlalchemy import Column, ForeignKey, Integer, MetaData

# Имена ограничениям раздаются здесь и только здесь: у первичных и внешних
# ключей своего имени нет, а без имени их потом не переделать — SQLite меняет
# схему пересозданием таблицы, и Alembic ищет ограничение по имени.
metadata = MetaData(
    naming_convention={
        "pk": "pk_%(table_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ix": "ix_%(table_name)s_%(column_0_name)s",
    }
)


def item_fk(**kwargs: Any) -> Column:
    """Ссылка на карточку. Со стороны каталога удаление каскадное —
    запрещающих ключей в схеме нет."""
    return Column(
        "item_id", Integer, ForeignKey("item.id", ondelete="CASCADE"), **kwargs
    )


def genre_fk(**kwargs: Any) -> Column:
    """Ссылка на жанр. Каскад по той же причине, что и у карточки."""
    return Column(
        "genre_id", Integer, ForeignKey("genre.id", ondelete="CASCADE"), **kwargs
    )
