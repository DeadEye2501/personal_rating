"""Всё, что источник отдал о карточке, в наших типах."""

from dataclasses import dataclass, field

from backend.model.credit import Credit
from backend.model.external import ExternalId, ExternalRating
from backend.model.item import Item
from backend.model.kinds import GenreSource


@dataclass(frozen=True, slots=True)
class SourceCard:
    """У `item` поле `id` равно нулю: строки в базе ещё нет. Тот же уговор,
    что у `new_manual_item`."""

    item: Item
    # Пары «пространство и метка» — по той же причине, что у `SearchHit`:
    # справочник у каждого источника свой, и метка без него не разбирается.
    genre_ext_ids: tuple[tuple[GenreSource, str], ...] = field(default_factory=tuple)
    people: tuple[Credit, ...] = field(default_factory=tuple)
    # Люди приходят только от TMDB, студии — только от магазинов, и пусто у
    # каждого из них своё, а не общее «данных нет».
    companies: tuple[Credit, ...] = field(default_factory=tuple)
    external_ids: tuple[ExternalId, ...] = field(default_factory=tuple)
    ratings: tuple[ExternalRating, ...] = field(default_factory=tuple)
