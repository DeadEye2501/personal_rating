"""Строители данных для тестов: карточки, кандидаты, картинки, записанное."""

import io
import json
from datetime import datetime
from pathlib import Path

from PIL import Image

from backend.model import (
    Credit,
    Item,
    Kind,
    PersonRole,
    SearchHit,
    Source,
    SourceCard,
)
from backend.storage.repository.library import LibraryRepository
from backend.storage.repository.ratings import RatingsRepository

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def recorded(relative: str):
    """Тело записанного ответа источника. JSON разбирается, всё прочее идёт
    текстом.

    Здесь, а не у клиентов источников: записанные ответы нужны и проверкам
    собранного бэкенда — там, где по мёртвой сети наблюдать нечего."""
    path = FIXTURES / relative
    text = path.read_text(encoding="utf-8")
    return json.loads(text) if path.suffix == ".json" else text


# Момент и момент позже. Заведённые в каждом модуле заново, они расходились
# значениями, ничего этим не проверяя. Важен только порядок: где нужен
# определённый промежуток, тест берёт `MOMENT + timedelta(...)`.
MOMENT = datetime(2026, 7, 29, 12, 0)
LATER = datetime(2026, 7, 30, 12, 0)

# Байты «картинки»: подпись PNG и набивка. Обрабатывать её никто не пытается,
# хранилищу постеров важно только то, что байты вернулись теми же.
PICTURE = b"\x89PNG\r\n\x1a\n" + b"0" * 512


def an_item(source_id: str, title: str, **fields) -> Item:
    """Незаписанная карточка: опознание аргументами, остальное по вкусу теста.

    Умолчания — фильм от TMDB: таких проверок больше всего, а `Item` требует
    шесть полей, и повторять их в каждом тесте значит спрятать среди них то
    одно, ради которого тест написан."""
    return Item(
        id=0,
        kind=fields.pop("kind", Kind.MOVIE),
        source=fields.pop("source", Source.TMDB),
        source_id=source_id,
        title=title,
        synced_at=fields.pop("synced_at", MOMENT),
        **fields,
    )


async def rated(sessions, source_id: str, score: float | None, **fields) -> int:
    """Записанная карточка со своей оценкой — или без неё, если оценки нет.

    Оценка ставится отдельным вызовом, как в приложении: карточка приезжает из
    источника, оценку выставляет человек."""
    fields.setdefault("year", 2014)
    item_id = await LibraryRepository(sessions).create(
        an_item(source_id, fields.pop("title", f"Фильм {source_id}"), **fields)
    )
    if score is not None:
        await RatingsRepository(sessions).set_score(item_id, score, now=MOMENT)
    return item_id


def picture(width: int, height: int, fmt: str = "PNG") -> bytes:
    """Настоящая картинка заданного размера. Размер обязателен: там, где эта
    картинка нужна, он и есть предмет проверки."""
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (10, 20, 30)).save(buffer, format=fmt)
    return buffer.getvalue()


# Готовая обложка: 2:3 — форма постера, а не случайные числа, и объявлена она
# один раз. Здесь же, чтобы три модуля не рисовали по картинке на импорте.
POSTER = picture(600, 900, fmt="JPEG")


STORES = (Source.STEAM, Source.GOG, Source.OLD_GAMES)


def hit(source_id: str = "157336", title: str = "Интерстеллар",
        **fields) -> SearchHit:
    """Короткий кандидат выдачи: опознание аргументами, остальное по вкусу теста.

    Умолчания уезжают в `base`, а не в подпись: иначе вызов `hit(kind=Kind.GAME)`
    даёт «got multiple values for keyword argument».

    Тип выводится из источника, а не стоит кино всегда. Магазины ничего, кроме
    игр, не отдают, и строка `Kind.MOVIE` с `source=Source.STEAM` — состояние,
    которого в производстве не бывает. Стоило оно дорого: `merged` выходит из
    склейки по **первой** не-игре, и шесть проверок игрового пути исполнялись
    мимо неё вовсе, а по именам и докстрингам выглядели исполняющимися."""
    source = fields.get("source", Source.TMDB)
    base = dict(kind=Kind.GAME if source in STORES else Kind.MOVIE,
                source=Source.TMDB)
    return SearchHit(source_id=source_id, title=title, **(base | fields))


def row(source: Source, source_id: str, title: str, **fields) -> SearchHit:
    """Тот же кандидат, но источником вперёд и без умолчаний.

    Отдельным именем, а не вызовом `hit` по месту: у проверок склейки источник
    — главное в свидетеле, и читаются они глазами именно по нему. Умолчаний нет
    нарочно: склейка смотрит на все три поля разом, и подставленное молча
    сделало бы свидетеля не тем, чем он выглядит."""
    return hit(source_id, title, source=source, **fields)


def titles(answers: list[list[SearchHit]]) -> list[str]:
    """Названия всех строк всех выдач подряд — то, что видно на экране."""
    return [one.title for answer in answers for one in answer]


def album_card(source_id: str = "54717452", **overrides) -> SourceCard:
    """Альбом из Deezer: исполнитель на месте режиссёра, треки своим полем.

    Здесь, а не у одного из двух модулей проверок: альбом нужен и писателю, и
    привязке, и своими копиями они разъехались бы молча — у одной из двух
    свидетель перестал бы быть тем, чем выглядит. Лейбла нет вовсе: он не
    берётся решением пользователя 22.08.2026."""
    fields = dict(
        item=an_item(source_id, "Группа крови", kind=Kind.MUSIC,
                     source=Source.DEEZER, year=1988,
                     poster_url="https://example.com/p.jpg"),
        people=(Credit("Кино", PersonRole.PERFORMER,
                       source=Source.DEEZER, source_id="4505880"),),
        tracks=("Группа крови", "Закрой за мной дверь"),
    )
    fields.update(overrides)
    return SourceCard(**fields)
