"""Куски чужого ответа, которые все источники переводят одинаково."""

from datetime import datetime

from backend.model import ExternalRating, GenreSource, RatingSource


def genres(space: GenreSource, rows: list[dict]) -> tuple[tuple[GenreSource, str], ...]:
    """Жанры в детальном ответе — объекты с именем, а номер лежит внутри. Имя
    нам не нужно: справочник переводит чужой номер в наш жанр сам."""
    return tuple((space, str(row["id"])) for row in rows)


def rating(
    source: RatingSource, value: float | int | None, now: datetime
) -> tuple[ExternalRating, ...]:
    """Одна оценка или ни одной.

    Ноль считается отсутствием: у TMDB `vote_average` равен нулю, пока фильм не
    оценил никто, и записать его значило бы объявить, что фильм оценили в ноль."""
    if not value:
        return ()
    return (ExternalRating(source=source, value=float(value), fetched_at=now),)
