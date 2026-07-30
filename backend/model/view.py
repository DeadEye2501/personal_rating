"""Карточка в том виде, в каком её показывает лента."""

from dataclasses import dataclass
from datetime import datetime

from backend.model.credit import Credit
from backend.model.external import ExternalId, ExternalRating
from backend.model.genre import Genre
from backend.model.item import Item
from backend.model.kinds import Kind, Source
from backend.model.rating import Rating
from backend.model.search import SearchHit


@dataclass(frozen=True, slots=True)
class Tag:
    """Своя метка. В отличие от жанра, снаружи не приходит никогда."""

    id: int
    name: str


@dataclass(frozen=True, slots=True)
class CardView:
    """Всё, что показывает карточка ленты, одним объектом.

    Кандидат из выдачи и карточка из базы — это один тип: виджет у них общий, а
    строки, которых нет в ответе поиска, просто пустуют. Отличает их item_id."""

    kind: Kind
    source: Source
    source_id: str
    title: str

    item_id: int | None = None
    original_title: str = ""
    year: int | None = None
    synopsis: str = ""
    poster_url: str = ""
    runtime: int | None = None
    seasons_count: int | None = None
    episodes_count: int | None = None
    synced_at: datetime | None = None

    genres: tuple[Genre, ...] = ()
    tags: tuple[Tag, ...] = ()
    people: tuple[Credit, ...] = ()
    companies: tuple[Credit, ...] = ()
    external: tuple[ExternalRating, ...] = ()
    # На них собираются ссылки «открыть на IMDb» из карточки. Тащить их
    # отдельным запросом на карточку — ровно та цена, ради устранения которой
    # заведено пачечное чтение.
    external_ids: tuple[ExternalId, ...] = ()
    rating: Rating | None = None
    in_wishlist: bool = False


def view_from_hit(hit: SearchHit, genres: tuple[Genre, ...] = (),
                  external: tuple[ExternalRating, ...] = ()) -> CardView:
    """Кандидат в выдаче. Жанры разворачивает справочник — в самом ответе поиска
    приходят голые идентификаторы; оценку собирает тот, кто знает источники.

    Ни то, ни другое здесь не считается нарочно: и справочник жанров, и таблица
    «у кого оценка приезжает даром» — знание вне типов границы слоёв."""
    return CardView(
        kind=hit.kind,
        source=hit.source,
        source_id=hit.source_id,
        title=hit.title,
        original_title=hit.original_title,
        year=hit.year,
        synopsis=hit.synopsis,
        poster_url=hit.poster_url,
        genres=genres,
        external=external,
    )


def view_from_item(item: Item) -> CardView:
    """Карточка из базы без довесков: жанры, теги, состав и оценки доливает
    ViewsRepository. Здесь только поля самой строки item."""
    return CardView(
        item_id=item.id,
        kind=item.kind,
        source=item.source,
        source_id=item.source_id,
        title=item.title,
        original_title=item.original_title,
        year=item.year,
        synopsis=item.synopsis,
        poster_url=item.poster_url,
        runtime=item.runtime,
        seasons_count=item.seasons_count,
        episodes_count=item.episodes_count,
        synced_at=item.synced_at,
    )
