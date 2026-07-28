"""Таблицы каталога: то, что наполняется из источников."""

from sqlalchemy import (
    Column,
    Date,
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

from backend.storage.tables.base import genre_fk, item_fk, metadata

item = Table(
    "item", metadata,
    Column("id", Integer, primary_key=True),
    Column("kind", Text, nullable=False),
    Column("source", Text, nullable=False),
    Column("source_id", Text, nullable=False),
    Column("title", Text, nullable=False),
    Column("original_title", Text),
    Column("year", Integer),
    Column("released_at", Date),
    Column("synopsis", Text),
    Column("poster_url", Text),
    Column("runtime", Integer),
    Column("seasons_count", Integer),
    Column("episodes_count", Integer),
    Column("synced_at", DateTime, nullable=False),
    UniqueConstraint("source", "source_id", name="uq_item_source"),
    Index("ix_item_kind", "kind"),
    Index("ix_item_kind_year", "kind", "year"),
)

genre = Table(
    "genre", metadata,
    Column("id", Integer, primary_key=True),
    Column("name", Text, nullable=False),
    Column("kind", Text, nullable=False),
    UniqueConstraint("name", "kind", name="uq_genre_name_kind"),
)

# Ключ включает genre_id: один внешний идентификатор разворачивается в два
# наших, потому что у TMDB в сериалах есть сборные жанры.
genre_map = Table(
    "genre_map", metadata,
    Column("source", Text, nullable=False),
    Column("ext_id", Text, nullable=False),
    genre_fk(nullable=False),
    PrimaryKeyConstraint("source", "ext_id", "genre_id"),
)

item_genre = Table(
    "item_genre", metadata,
    item_fk(nullable=False),
    genre_fk(nullable=False),
    PrimaryKeyConstraint("item_id", "genre_id"),
    Index("ix_item_genre_genre_id", "genre_id"),
)

# Источник необязателен: у Steam и GOG людей нет вовсе, а студии приходят
# голыми строками без идентификаторов. Склейка таких идёт по имени, и от
# размножения написаний защищает подсказка при вводе, а не база.
person = Table(
    "person", metadata,
    Column("id", Integer, primary_key=True),
    Column("name", Text, nullable=False),
    Column("source", Text),
    Column("source_id", Text),
    UniqueConstraint("source", "source_id", name="uq_person_source"),
)

# Роль входит в ключ: один человек бывает на карточке и режиссёром, и актёром.
person_credit = Table(
    "person_credit", metadata,
    item_fk(nullable=False),
    Column("person_id", Integer, ForeignKey("person.id", ondelete="CASCADE"),
           nullable=False),
    Column("role", Text, nullable=False),
    Column("position", Integer),
    PrimaryKeyConstraint("item_id", "person_id", "role"),
    Index("ix_person_credit_person_id", "person_id"),
)

company = Table(
    "company", metadata,
    Column("id", Integer, primary_key=True),
    Column("name", Text, nullable=False),
    Column("source", Text),
    Column("source_id", Text),
    UniqueConstraint("source", "source_id", name="uq_company_source"),
)

company_credit = Table(
    "company_credit", metadata,
    item_fk(nullable=False),
    Column("company_id", Integer, ForeignKey("company.id", ondelete="CASCADE"),
           nullable=False),
    Column("role", Text, nullable=False),
    PrimaryKeyConstraint("item_id", "company_id", "role"),
    Index("ix_company_credit_company_id", "company_id"),
)

external_id = Table(
    "external_id", metadata,
    item_fk(nullable=False),
    Column("source", Text, nullable=False),
    Column("value", Text, nullable=False),
    PrimaryKeyConstraint("item_id", "source"),
    UniqueConstraint("source", "value", name="uq_external_id_value"),
)

# Пустой value — это ответ «у источника такой оценки нет», а не отсутствие
# ответа. Отсутствие ответа — это отсутствие строки.
external_rating = Table(
    "external_rating", metadata,
    item_fk(nullable=False),
    Column("source", Text, nullable=False),
    Column("value", Float),
    Column("fetched_at", DateTime, nullable=False),
    PrimaryKeyConstraint("item_id", "source"),
)
