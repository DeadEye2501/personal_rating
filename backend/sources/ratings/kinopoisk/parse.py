"""Перевод ответов обоих зеркал Кинопоиска в наши типы."""

from datetime import datetime

from backend.model import ExternalId, ExternalRating, Ratings, RatingSource, IdSource


def _rating(value, now: datetime) -> tuple[ExternalRating, ...]:
    # Ноль — это значение, а не отсутствие: проверяем на None, а не на ложность.
    if value is None:
        return ()
    return (
        ExternalRating(source=RatingSource.KINOPOISK, value=float(value),
                       fetched_at=now),
    )


def _ident(value) -> tuple[ExternalId, ...]:
    if value is None:
        return ()
    return (ExternalId(source=IdSource.KINOPOISK, value=str(value)),)


def parse_poiskkino(payload: dict) -> Ratings:
    docs = payload.get("docs") or []
    if not docs:
        return Ratings()

    row = docs[0]
    now = datetime.now()
    return Ratings(
        values=_rating((row.get("rating") or {}).get("kp"), now),
        external_ids=_ident(row.get("id")),
    )


def parse_unofficial(payload: dict) -> Ratings:
    items = payload.get("items") or []
    if not items:
        return Ratings()

    row = items[0]
    now = datetime.now()
    return Ratings(
        values=_rating(row.get("ratingKinopoisk"), now),
        external_ids=_ident(row.get("kinopoiskId")),
    )
