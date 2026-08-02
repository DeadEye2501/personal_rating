"""Поверхность схемы: отсюда таблицы берут репозитории."""

from backend.storage.tables.base import metadata
from backend.storage.tables.catalog import (
    company,
    company_credit,
    external_id,
    external_rating,
    genre,
    genre_rule,
    genre_rule_mark,
    item,
    item_genre,
    person,
    person_credit,
)
from backend.storage.tables.mine import item_tag, rating, tag, wishlist

__all__ = [
    "company",
    "company_credit",
    "external_id",
    "external_rating",
    "genre",
    "genre_rule",
    "genre_rule_mark",
    "item",
    "item_genre",
    "item_tag",
    "metadata",
    "person",
    "person_credit",
    "rating",
    "tag",
    "wishlist",
]
