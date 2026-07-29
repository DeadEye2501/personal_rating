"""Перевод ответов TMDB в наши типы."""

from datetime import date, datetime

from backend.model import (
    Credit,
    ExternalId,
    ExternalRating,
    GenreSource,
    IdSource,
    Item,
    Kind,
    PersonRole,
    RatingSource,
    SearchHit,
    Source,
    SourceCard,
)
from backend.sources.convert import genres, rating

POSTER_BASE = "https://image.tmdb.org/t/p/w500"


class Incomplete(Exception):
    """Источник ответил 200, но обещанного блока в ответе нет.

    Опечатка в `append_to_response` ошибки не даёт: приходит 200 и просто без
    блока. Поэтому полнота проверяется по содержимому, а не по коду."""


def _year(value: str | None) -> int | None:
    """У необъявленного к выходу дата приходит пустой строкой."""
    head = (value or "")[:4]
    return int(head) if head.isdigit() else None


def _released(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _poster(payload: dict) -> str:
    path = payload.get("poster_path")
    return f"{POSTER_BASE}{path}" if path else ""


def _genres(payload: dict) -> tuple[tuple[GenreSource, str], ...]:
    return genres(GenreSource.TMDB, payload.get("genres", []))


def _own_rating(payload: dict, now: datetime) -> tuple[ExternalRating, ...]:
    return rating(RatingSource.TMDB, payload.get("vote_average"), now)


def _imdb(value: str | None) -> tuple[ExternalId, ...]:
    """Пусто, если источник его не дал: без `imdb_id` не спросить ни MDBList,
    ни OMDB, ни Кинопоиск, но и записывать в связку нечего."""
    return (ExternalId(source=IdSource.IMDB, value=value),) if value else ()


def _person(row: dict, role: PersonRole, position: int | None = None) -> Credit:
    """Идентификатор человека приезжает в том же ответе, что и состав. Без
    него два разных актёра-тёзки склеились бы в одну строку молча."""
    return Credit(
        name=row["name"],
        role=role,
        position=position,
        source=Source.TMDB,
        source_id=str(row["id"]),
    )


def _cast(rows: list[dict]) -> list[Credit]:
    return [
        _person(row, PersonRole.ACTOR, row.get("order", index))
        for index, row in enumerate(rows)
    ]


def _required(payload: dict, block: str) -> dict:
    """Блок, без которого карточку записывать нельзя.

    Проверяется наличие, а не непустота: у документалки состав пуст
    по-настоящему, и такая карточка обязана сохраниться."""
    found = payload.get(block)
    if found is None or "cast" not in found:
        raise Incomplete(f"в ответе TMDB нет {block}.cast")
    return found


def parse_search(payload: dict, kind: Kind) -> list[SearchHit]:
    """У фильма название в title, у сериала — в name. Поле даты тоже разное."""
    is_series = kind is Kind.SERIES
    title_key = "name" if is_series else "title"
    original_key = "original_name" if is_series else "original_title"
    date_key = "first_air_date" if is_series else "release_date"

    hits = []
    for row in payload.get("results", []):
        hits.append(
            SearchHit(
                kind=kind,
                source=Source.TMDB,
                source_id=str(row["id"]),
                title=row.get(title_key) or "",
                original_title=row.get(original_key) or "",
                year=_year(row.get(date_key)),
                synopsis=row.get("overview") or "",
                poster_url=_poster(row),
                genre_ext_ids=tuple(
                    (GenreSource.TMDB, str(genre_id))
                    for genre_id in row.get("genre_ids", [])
                ),
                source_rating=row.get("vote_average") or None,
            )
        )
    return hits


def parse_movie(payload: dict) -> SourceCard:
    credits_block = _required(payload, "credits")
    people = _cast(credits_block["cast"])
    people += [
        _person(row, PersonRole.DIRECTOR)
        for row in credits_block.get("crew", [])
        if row.get("job") == "Director"
    ]

    now = datetime.now()
    return SourceCard(
        item=Item(
            id=0,
            kind=Kind.MOVIE,
            source=Source.TMDB,
            source_id=str(payload["id"]),
            title=payload.get("title") or "",
            synced_at=now,
            original_title=payload.get("original_title") or "",
            year=_year(payload.get("release_date")),
            released_at=_released(payload.get("release_date")),
            synopsis=payload.get("overview") or "",
            poster_url=_poster(payload),
            runtime=payload.get("runtime") or None,
        ),
        genre_ext_ids=_genres(payload),
        people=tuple(people),
        external_ids=_imdb(payload.get("imdb_id")),
        ratings=_own_rating(payload, now),
    )


def parse_series(payload: dict) -> SourceCard:
    people = _cast(_required(payload, "aggregate_credits")["cast"])
    people += [
        _person(row, PersonRole.SHOWRUNNER) for row in payload.get("created_by", [])
    ]

    now = datetime.now()
    return SourceCard(
        item=Item(
            id=0,
            kind=Kind.SERIES,
            source=Source.TMDB,
            source_id=str(payload["id"]),
            title=payload.get("name") or "",
            synced_at=now,
            original_title=payload.get("original_name") or "",
            year=_year(payload.get("first_air_date")),
            released_at=_released(payload.get("first_air_date")),
            synopsis=payload.get("overview") or "",
            poster_url=_poster(payload),
            seasons_count=payload.get("number_of_seasons"),
            episodes_count=payload.get("number_of_episodes"),
        ),
        genre_ext_ids=_genres(payload),
        people=tuple(people),
        # У сериала на верхнем уровне `imdb_id` нет вовсе — он в довеске.
        external_ids=_imdb((payload.get("external_ids") or {}).get("imdb_id")),
        ratings=_own_rating(payload, now),
    )
