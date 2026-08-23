"""Поверхность модели: отсюда типы границы слоёв импортирует клиент."""

from backend.model.card import SourceCard
from backend.model.credit import Credit
from backend.model.denied import (
    BadImage,
    Denied,
    Dangling,
    IdentityTaken,
    ItemExists,
    TagExists,
    WrongTagKind,
)
from backend.model.external import ExternalId, ExternalRating
from backend.model.genre import Genre, GenreRule
from backend.model.item import (
    Item,
    SeriesCounts,
    new_manual_item,
    new_source_id,
)
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
from backend.model.link import ExternalLink, parse_link
from backend.model.outcome import (
    Found,
    Missing,
    Outcome,
    Reason,
    Refusal,
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
from backend.model.results import (
    SEARCH_SIZE,
    ExternalSearch,
    merge_results,
)
from backend.model.search import PersonHit, SearchHit
from backend.model.suggestion import Suggestion
from backend.model.tag import Tag
from backend.model.view import CardView, view_from_hit, view_from_item


__all__ = [
    "SEARCH_SIZE",
    "BadImage",
    "Bucket",
    "CardView",
    "CompanyRole",
    "Credit",
    "Denied",
    "Dangling",
    "ExternalId",
    "ExternalLink",
    "ExternalRating",
    "ExternalSearch",
    "Feed",
    "Filters",
    "Found",
    "Genre",
    "GenreKind",
    "GenreRule",
    "GenreSource",
    "Histogram",
    "IdSource",
    "IdentityTaken",
    "Item",
    "ItemExists",
    "Kind",
    "Missing",
    "Order",
    "Outcome",
    "PersonHit",
    "PersonRole",
    "Rating",
    "RatingSource",
    "Ratings",
    "Reason",
    "Refusal",
    "SearchHit",
    "Section",
    "SeriesCounts",
    "Sort",
    "Source",
    "SourceCard",
    "Suggestion",
    "Tag",
    "TagExists",
    "WrongTagKind",
    "average_score",
    "merge_results",
    "new_manual_item",
    "new_source_id",
    "parse_link",
    "view_from_hit",
    "view_from_item",
]
