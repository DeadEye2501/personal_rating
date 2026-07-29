"""Перевод ответов MDBList в наши типы."""

from datetime import datetime

from backend.model import ExternalRating, Ratings, RatingSource

# Имя источника — это владелец оценки. Чужих владельцев не заводим: строка в
# `external_rating` должна значить одно и то же всегда. Поэтому `metacriticuser`
# и `trakt` отбрасываются — это не Metacritic и не то, что мы показываем.
OWNERS = {
    "imdb": RatingSource.IMDB,
    "tmdb": RatingSource.TMDB,
    "tomatoes": RatingSource.ROTTEN,
    "metacritic": RatingSource.METACRITIC,
}


def parse_ratings(payload: dict) -> Ratings:
    now = datetime.now()
    found = []
    for row in payload.get("ratings", []):
        owner = OWNERS.get(row.get("source"))
        if owner is None:
            continue
        value = row.get("value")
        # null — это «у них нет этой оценки». Отдаём пустым значением, а не
        # выбрасываем: иначе не отличить от «не спрашивали».
        found.append(
            ExternalRating(
                source=owner,
                value=None if value is None else float(value),
                fetched_at=now,
            )
        )
    return Ratings(values=tuple(found))
