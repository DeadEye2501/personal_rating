from dataclasses import dataclass
from datetime import datetime

from backend.model.kinds import IdSource, RatingSource


@dataclass(frozen=True, slots=True)
class ExternalId:
    source: IdSource
    value: str


@dataclass(frozen=True, slots=True)
class ExternalRating:
    source: RatingSource
    value: float | None   # пусто — источник такой оценки не знает
    fetched_at: datetime
