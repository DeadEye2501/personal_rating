"""Перевод ответов OMDB в наши типы."""

from datetime import datetime

from backend.model import ExternalRating, Ratings, RatingSource

OWNERS = {
    "Internet Movie Database": RatingSource.IMDB,
    "Rotten Tomatoes": RatingSource.ROTTEN,
    "Metacritic": RatingSource.METACRITIC,
}


def _number(raw: str | None) -> float | None:
    """OMDB отдаёт «8.6/10», «72%» и «74/100» — форма зависит от владельца, и
    значимая часть всегда стоит первой."""
    if not raw or raw == "N/A":
        return None
    head = raw.split("/")[0].rstrip("%").strip()
    try:
        return float(head)
    except ValueError:
        return None


def parse_ratings(payload: dict) -> Ratings:
    now = datetime.now()
    found = []
    seen = set()

    for row in payload.get("Ratings", []):
        owner = OWNERS.get(row.get("Source"))
        value = _number(row.get("Value"))
        if owner is None or value is None:
            continue
        found.append(ExternalRating(source=owner, value=value, fetched_at=now))
        seen.add(owner)

    # IMDb приезжает дважды — списком и отдельным полем. Второй раз берём
    # только если в списке его не было: в базе у владельца один ключ.
    imdb = _number(payload.get("imdbRating"))
    if imdb is not None and RatingSource.IMDB not in seen:
        found.append(
            ExternalRating(source=RatingSource.IMDB, value=imdb, fetched_at=now)
        )
    return Ratings(values=tuple(found))
