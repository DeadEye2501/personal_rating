"""Перевод ответов обоих зеркал Кинопоиска в наши типы."""

from datetime import datetime

from backend.model import ExternalRating, IdSource, Ratings, RatingSource
from backend.sources.convert import identifier


def _rating(value, now: datetime) -> tuple[ExternalRating, ...]:
    # Ноль — это значение, а не отсутствие: проверяем на None, а не на ложность.
    if value is None:
        return ()
    return (
        ExternalRating(source=RatingSource.KINOPOISK, value=float(value),
                       fetched_at=now),
    )


def _first_row(payload: dict, key: str) -> dict | None:
    """Нулевая строка ответа зеркала или `None`, если её нет.

    Ключ у зеркал разный, а пролог — один: взять список, на пустом вернуть
    «такого нет». Пути к значениям внутри строки тоже разные, и это уже
    содержание каждого разбора."""
    rows = payload.get(key) or []
    return rows[0] if rows else None


def parse_poiskkino(payload: dict) -> Ratings:
    row = _first_row(payload, "docs")
    if row is None:
        return Ratings()

    now = datetime.now()
    return Ratings(
        values=_rating((row.get("rating") or {}).get("kp"), now),
        external_ids=identifier(IdSource.KINOPOISK, row.get("id")),
    )


def parse_unofficial(payload: dict) -> Ratings:
    row = _first_row(payload, "items")
    if row is None:
        return Ratings()

    now = datetime.now()
    return Ratings(
        values=_rating(row.get("ratingKinopoisk"), now),
        external_ids=identifier(IdSource.KINOPOISK, row.get("kinopoiskId")),
    )
