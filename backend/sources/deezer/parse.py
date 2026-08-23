"""Перевод ответов Deezer в наши типы."""

from datetime import datetime

from backend.model import (
    Credit,
    GenreSource,
    Item,
    Kind,
    PersonHit,
    PersonRole,
    SearchHit,
    Source,
    SourceCard,
)
from backend.sources.convert import found_people, genres, year

# Чем Deezer помечает «жанра нет» в строке выдачи. Не пустота и не `null`:
# замерено, у альбома без жанра там `-1`, и записанный как есть он ушёл бы в
# справочник меткой, которой у источника не существует.
NO_GENRE = -1


def _cover(payload: dict) -> str:
    """Обложка приходит готовым адресом, собирать нечего: `cover_xl` — это
    1000×1000, то есть квадрат, а не афиша."""
    return payload.get("cover_xl") or ""


def _mark(payload: dict) -> tuple[tuple[GenreSource, str], ...]:
    """Жанр строки выдачи. В ней он один и лежит числом, а список `genres`
    приезжает только в карточке."""
    found = payload.get("genre_id")
    if found is None or found == NO_GENRE:
        return ()
    return ((GenreSource.DEEZER, str(found)),)


def parse_albums(payload: dict) -> list[SearchHit]:
    """Строка выдачи несёт всё, кроме треков и полного списка жанров.

    Разбирает две ручки: поиск альбомов и альбомы исполнителя. Отличаются они
    одним — года в строках поиска нет вовсе, а в альбомах исполнителя он есть у
    каждой, замерено 23.08.2026. Читается он поэтому по наличию: своей ветки
    под ручку заводить не за чем, поле просто пустое у одной из двух."""
    return [
        SearchHit(
            kind=Kind.MUSIC,
            source=Source.DEEZER,
            source_id=str(row["id"]),
            title=row.get("title") or "",
            year=year(row.get("release_date")),
            poster_url=_cover(row),
            genre_ext_ids=_mark(row),
        )
        for row in payload.get("data", [])
    ]


def parse_artists(payload: dict) -> list[PersonHit]:
    """Найденные приезжают все — правило от 31.07.2026, общее у всех
    источников, и живёт оно в `convert.found_people`. Здесь остаётся имя ключа:
    у Deezer список лежит в `data`, у TMDB в `results`."""
    return found_people(payload.get("data", []))


def parse_card(payload: dict) -> SourceCard:
    """Исполнитель встаёт туда, где у фильма режиссёр, а треки — своим полем.

    Треком человек не является, и в титры он не попадает: иначе «Группа крови»
    предлагалась бы в подсказке при вводе имени. Порядок треков берётся по месту
    в списке — `track_position` у Deezer пуст у всех, замерено.

    Лейбл не берётся решением пользователя 22.08.2026: `label` у него не имя
    лейбла, а список правообладателей, обрезанный сервисом на сотне знаков.
    Синопсиса у альбома нет вовсе, `original_title` пуст."""
    artist = payload.get("artist") or {}
    return SourceCard(
        item=Item(
            id=0,
            kind=Kind.MUSIC,
            source=Source.DEEZER,
            source_id=str(payload["id"]),
            title=payload.get("title") or "",
            synced_at=datetime.now(),
            year=year(payload.get("release_date")),
            poster_url=_cover(payload),
        ),
        genre_ext_ids=genres(GenreSource.DEEZER,
                             (payload.get("genres") or {}).get("data", [])),
        people=(Credit(name=artist.get("name") or "",
                       role=PersonRole.PERFORMER,
                       source=Source.DEEZER,
                       source_id=str(artist["id"])),) if artist else (),
        tracks=tuple(one.get("title") or ""
                     for one in (payload.get("tracks") or {}).get("data", [])),
    )
