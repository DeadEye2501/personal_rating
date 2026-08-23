"""Перевод ответов Google Books в наши типы."""

import re
from datetime import datetime

from bs4 import BeautifulSoup

from backend.model import (
    CompanyRole,
    Credit,
    GenreSource,
    Item,
    Kind,
    PersonRole,
    SearchHit,
    Source,
    SourceCard,
)
from backend.sources.convert import year
from backend.unique import unique

# Второй уровень пути, который ничего не уточняет: `Fiction / General` — это
# «художественная, и больше Google не сказал».
_GENERAL = "General"

_ZOOM = re.compile(r"zoom=\d+")


def _genre_mark(path: str) -> str:
    """Второй уровень пути BISAC, а где его нет или он `General` — первый.

    Третий слишком дробен: у одной книги разом `Hard Science Fiction` и
    `Space Exploration`. Первый слишком крупен: `Fiction` покрывает треть всех
    книг."""
    parts = [one.strip() for one in path.split("/") if one.strip()]
    if len(parts) > 1 and parts[1] != _GENERAL:
        return parts[1]
    return parts[0] if parts else ""


def _marks(info: dict) -> tuple[tuple[GenreSource, str], ...]:
    """Повторы снимаются: у «Задачи трёх тел» четыре пути BISAC и один и тот же
    второй уровень у всех четырёх — жанр встал бы в карточке четырьмя
    одинаковыми метками."""
    marks = [_genre_mark(path) for path in info.get("categories", [])]
    return tuple((GenreSource.GOOGLE_BOOKS, mark) for mark in unique(marks) if mark)


def _poster(info: dict) -> str:
    """Подмена масштаба, а не сборка адреса заново: у части томов в хвосте
    стоит токен `imgtk`, без которого картинка не отдаётся. `zoom=3` — 575×883
    против 300×461 у второго, замерено на обоих видах адреса."""
    thumbnail = info.get("imageLinks", {}).get("thumbnail", "")
    return _ZOOM.sub("zoom=3", thumbnail) if thumbnail else ""


def _plain(value: str | None) -> str:
    """Синопсис без разметки: замерено, у «Задачи трёх тел» весь текст обёрнут
    в `<p>`. Страница показывает синопсис текстом и экранирует его — теги
    приехали бы человеку дословно.

    Разбирает `bs4`, как и страницы old-games.ru: свой отрезатель регуляркой не
    знает про сущности вроде `&nbsp;`."""
    if not value:
        return ""
    return BeautifulSoup(value, "html.parser").get_text(" ", strip=True)


def _info(payload: dict) -> dict:
    """Всё о томе лежит одним блоком, и он же приезжает строкой выдачи."""
    return payload.get("volumeInfo") or {}


def parse_search(payload: dict) -> list[SearchHit]:
    """Строка выдачи несёт всё, кроме полного пути жанра: его обрезает сам
    Google до верхушки — замерено, у «Задачи трёх тел» в выдаче `Fiction`, а в
    карточке `Fiction / Science Fiction / Hard Science Fiction`."""
    hits = []
    for row in payload.get("items", []):
        info = _info(row)
        hits.append(
            SearchHit(
                kind=Kind.BOOK,
                source=Source.GOOGLE_BOOKS,
                source_id=str(row["id"]),
                title=info.get("title") or "",
                year=year(info.get("publishedDate")),
                synopsis=_plain(info.get("description")),
                poster_url=_poster(info),
                genre_ext_ids=_marks(info),
            )
        )
    return hits


def parse_card(payload: dict) -> SourceCard:
    """Идентичности у автора нет вовсе: `authors` — голые строки, и суррогат
    склеил бы двух тёзок в одну строку навсегда. Таких склеивают по имени, как
    студии магазинов.

    `original_title` остаётся пустым: второго названия у Google нет ни одного."""
    info = _info(payload)
    publisher = info.get("publisher")
    now = datetime.now()
    return SourceCard(
        item=Item(
            id=0,
            kind=Kind.BOOK,
            source=Source.GOOGLE_BOOKS,
            source_id=str(payload["id"]),
            title=info.get("title") or "",
            synced_at=now,
            year=year(info.get("publishedDate")),
            synopsis=_plain(info.get("description")),
            poster_url=_poster(info),
        ),
        genre_ext_ids=_marks(info),
        people=tuple(Credit(name=name, role=PersonRole.AUTHOR)
                     for name in info.get("authors", [])),
        companies=((Credit(name=publisher, role=CompanyRole.PUBLISHER),)
                   if publisher else ()),
    )
