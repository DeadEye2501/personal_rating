"""Таблицы моих данных: то, что заводит и правит человек.

От источника они не зависят — кроме одной: у `removed` источник
составляет ключ, потому что помнить надо строку чужой выдачи, а не
свою карточку. Своей к тому моменту уже нет."""

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    PrimaryKeyConstraint,
    Table,
    Text,
    UniqueConstraint,
)

from backend.storage.tables.base import item_fk, metadata

# Что человек убрал из выдачи насовсем. Своих данных таблица не хранит и на
# `item` не ссылается вовсе: карточка к этому моменту удалена по-настоящему, а
# помнить надо ровно то, чем строка выдачи опознаётся до всякой загрузки.
#
# `kind` в ключе обязателен, и это не перестраховка: у TMDB фильмы и сериалы
# нумеруются в разных пространствах и сталкиваются числами. Без него удалённый
# фильм `tmdb/1399` молча унёс бы с собой сериал «Игра престолов» — ровно то
# ложное срабатывание, которого у этой пары «не бывает по построению».
#
# Название последним полем — человеку: обратного хода в приложении нет, чинить
# придётся руками из SQLite, а по паре «steam / 38410» не понять, что это было.
removed = Table(
    "removed", metadata,
    Column("kind", Text, nullable=False),
    Column("source", Text, nullable=False),
    Column("source_id", Text, nullable=False),
    Column("title", Text, nullable=False),
    PrimaryKeyConstraint("kind", "source", "source_id"),
)

rating = Table(
    "rating", metadata,
    item_fk(primary_key=True),
    Column("score", Float),
    Column("visual", Integer),
    Column("narrative", Integer),
    Column("gameplay", Integer),
    Column("review", Text),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),

    Index("ix_rating_score", "score"),
    Index("ix_rating_updated_at", "updated_at"),
)

tag = Table(
    "tag", metadata,
    Column("id", Integer, primary_key=True),
    Column("name", Text, nullable=False),
    Column("kind", Text, nullable=False),
    Column("position", Integer, nullable=False),
    UniqueConstraint("name", "kind", name="uq_tag_name_kind"),
)

item_tag = Table(
    "item_tag", metadata,
    item_fk(nullable=False),
    Column("tag_id", Integer, ForeignKey("tag.id", ondelete="CASCADE"),
           nullable=False),
    PrimaryKeyConstraint("item_id", "tag_id"),
    Index("ix_item_tag_tag_id", "tag_id"),
)

wishlist = Table(
    "wishlist", metadata,
    item_fk(primary_key=True),
    Column("added_at", DateTime, nullable=False),
    Index("ix_wishlist_added_at", "added_at"),
)
