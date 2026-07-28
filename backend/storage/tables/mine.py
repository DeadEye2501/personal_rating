"""Таблицы моих данных: то, что не зависит от источника."""

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
