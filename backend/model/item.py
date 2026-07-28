"""Карточка любого типа содержимого на границе слоёв."""

from dataclasses import dataclass
from datetime import date, datetime

from backend.model.kinds import Kind, Source


@dataclass(frozen=True, slots=True)
class Item:
    id: int
    kind: Kind
    source: Source
    source_id: str
    title: str
    synced_at: datetime

    original_title: str = ""
    year: int | None = None
    released_at: date | None = None
    synopsis: str = ""
    poster_url: str = ""
    runtime: int | None = None          # минуты, только у фильма
    seasons_count: int | None = None    # только у сериала
    episodes_count: int | None = None   # всего серий, только у сериала
