"""Перевод ответов TMDB в наши типы."""

from backend.model import GenreSource, Kind, SearchHit, Source

POSTER_BASE = "https://image.tmdb.org/t/p/w500"


def _year(value: str | None) -> int | None:
    """У необъявленного к выходу дата приходит пустой строкой."""
    head = (value or "")[:4]
    return int(head) if head.isdigit() else None


def parse_search(payload: dict, kind: Kind) -> list[SearchHit]:
    """У фильма название в title, у сериала — в name. Поле даты тоже разное."""
    is_series = kind is Kind.SERIES
    title_key = "name" if is_series else "title"
    original_key = "original_name" if is_series else "original_title"
    date_key = "first_air_date" if is_series else "release_date"

    hits = []
    for row in payload.get("results", []):
        poster = row.get("poster_path")
        hits.append(
            SearchHit(
                kind=kind,
                source=Source.TMDB,
                source_id=str(row["id"]),
                title=row.get(title_key) or "",
                original_title=row.get(original_key) or "",
                year=_year(row.get(date_key)),
                synopsis=row.get("overview") or "",
                poster_url=f"{POSTER_BASE}{poster}" if poster else "",
                genre_ext_ids=tuple(
                    (GenreSource.TMDB, str(genre_id))
                    for genre_id in row.get("genre_ids", [])
                ),
                source_rating=row.get("vote_average") or None,
            )
        )
    return hits
