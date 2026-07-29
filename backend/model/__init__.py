"""Поверхность модели: отсюда типы границы слоёв импортирует клиент."""

from backend.model.card import SourceCard
from backend.model.credit import Credit
from backend.model.external import ExternalId, ExternalRating
from backend.model.genre import Genre
from backend.model.item import Item, new_manual_item, new_source_id
from backend.model.kinds import (
    CompanyRole,
    GenreKind,
    GenreSource,
    IdSource,
    Kind,
    PersonRole,
    RatingSource,
    Source,
)
from backend.model.rating import Rating, average_score
from backend.model.ratings import Ratings
from backend.model.search import SearchHit
from backend.model.suggestion import Suggestion

__all__ = [
    "CompanyRole",
    "Credit",
    "ExternalId",
    "ExternalRating",
    "Genre",
    "GenreKind",
    "GenreSource",
    "IdSource",
    "Item",
    "Kind",
    "PersonRole",
    "Rating",
    "RatingSource",
    "Ratings",
    "SearchHit",
    "Source",
    "SourceCard",
    "Suggestion",
    "average_score",
    "new_manual_item",
    "new_source_id",
]
