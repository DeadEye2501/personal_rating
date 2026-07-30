"""Поверхность модели: отсюда типы границы слоёв импортирует клиент."""

from backend.model.card import SourceCard
from backend.model.credit import Credit
from backend.model.external import ExternalId, ExternalRating
from backend.model.genre import Genre
from backend.model.item import (
    Item,
    SeriesCounts,
    new_manual_item,
    new_source_id,
)
from backend.model.link import ExternalLink, parse_link
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
from backend.model.query import (
    Bucket,
    Feed,
    Filters,
    Histogram,
    Order,
    Section,
    Sort,
)
from backend.model.rating import Rating, average_score
from backend.model.ratings import Ratings
from backend.model.search import SearchHit
from backend.model.suggestion import Suggestion
from backend.model.results import merge_results
from backend.model.view import CardView, Tag, view_from_hit, view_from_item

__all__ = [
    "Bucket",
    "CardView",
    "CompanyRole",
    "Credit",
    "ExternalId",
    "ExternalLink",
    "ExternalRating",
    "Feed",
    "Filters",
    "Genre",
    "GenreKind",
    "GenreSource",
    "Histogram",
    "IdSource",
    "Item",
    "Kind",
    "Order",
    "PersonRole",
    "Rating",
    "RatingSource",
    "Ratings",
    "SearchHit",
    "Section",
    "SeriesCounts",
    "Sort",
    "Source",
    "SourceCard",
    "Suggestion",
    "Tag",
    "average_score",
    "merge_results",
    "new_manual_item",
    "new_source_id",
    "parse_link",
    "view_from_hit",
    "view_from_item",
]
