"""Перевод ответов GOG в наши типы."""

from datetime import datetime

from backend.model import (
    GenreSource,
    Item,
    Kind,
    RatingSource,
    SearchHit,
    Source,
    SourceCard,
)
from backend.sources.convert import companies, genres, rating, year


def _marks(row: dict) -> tuple[tuple[GenreSource, str], ...]:
    """Жанры и теги приезжают одним ответом и разными пространствами: `fantasy`
    у GOG — и жанр, и тег, а в справочнике это разные строки. Идентификатор —
    слаг, и в нём у них живёт опечатка `rougelike`: сопоставляем по слагу, а не
    по названию, потому что название переводится, а слаг нет."""
    return genres(GenreSource.GOG, row.get("genres", []), key="slug") + genres(
        GenreSource.GOG_TAG, row.get("tags", []), key="slug"
    )


def parse_catalog(payload: dict) -> list[SourceCard]:
    """У GOG поиск и карточка — один запрос: отдельный детальный не нужен."""
    now = datetime.now()
    return [
        SourceCard(
            item=Item(
                id=0,
                kind=Kind.GAME,
                source=Source.GOG,
                source_id=str(row["id"]),
                # Локализованы у GOG только жанры: название английское.
                title=row.get("title") or "",
                synced_at=now,
                year=year(row.get("releaseDate")),
                poster_url=row.get("coverVertical") or "",
            ),
            genre_ext_ids=_marks(row),
            companies=companies(row),
            # Оценка игроков лежит в `reviewsRating`; `ratings` у GOG — это
            # возрастные рейтинги, PEGI и ESRB, и оценкой игры они не являются.
            ratings=rating(RatingSource.GOG, row.get("reviewsRating"), now),
        )
        for row in payload.get("products", [])
    ]


def to_hit(card: SourceCard) -> SearchHit:
    """Наружу поиск отдаёт кандидатов, как TMDB и Steam."""
    return SearchHit(
        kind=card.item.kind,
        source=card.item.source,
        source_id=card.item.source_id,
        title=card.item.title,
        year=card.item.year,
        poster_url=card.item.poster_url,
        genre_ext_ids=card.genre_ext_ids,
        source_rating=card.ratings[0].value if card.ratings else None,
    )
