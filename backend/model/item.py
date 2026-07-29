"""Карточка любого типа содержимого на границе слоёв."""

from dataclasses import dataclass
from datetime import date, datetime
from uuid import uuid4

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


def new_source_id() -> str:
    """Идентичность ручной карточки. Случайная, а не `item.id`: тот известен
    только после вставки, и строку пришлось бы писать дважды. Предсказуемый
    номер столкнулся бы с заведённой руками карточкой на ключе уникальности."""
    return str(uuid4())


def new_manual_item(kind: Kind, title: str, **fields) -> Item:
    """Карточка, заведённая руками.

    `synced_at` подставляется сам — у ручной карточки это момент создания."""
    fields.setdefault("synced_at", datetime.now())
    return Item(
        id=0,
        kind=kind,
        source=Source.MANUAL,
        source_id=new_source_id(),
        title=title,
        **fields,
    )
