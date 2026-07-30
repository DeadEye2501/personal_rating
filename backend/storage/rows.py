"""Строки базы в типы границы слоёв.

Собраны в одном месте потому, что читателей у каждой таблицы двое: репозиторий
своего признака отвечает про одну карточку, `ViewsRepository` — про страницу
пачкой. Две копии сборки расходились бы полями молча."""

from sqlalchemy import Row

from backend.storage.repository.entity import Entity

from backend.model import (
    Credit,
    ExternalId,
    ExternalRating,
    Genre,
    GenreKind,
    IdSource,
    Item,
    Kind,
    Rating,
    RatingSource,
    Source,
    Tag,
)


def to_item(row: Row) -> Item:
    """Пустой текст отдаётся пустой строкой, а не `None`: карточку правит и
    человек, и в его строке колонка бывает пустой — а в интерфейс `None`
    уехало бы словом «None»."""
    return Item(
        id=row.id,
        kind=Kind(row.kind),
        source=Source(row.source),
        source_id=row.source_id,
        title=row.title,
        synced_at=row.synced_at,
        original_title=row.original_title or "",
        year=row.year,
        released_at=row.released_at,
        synopsis=row.synopsis or "",
        poster_url=row.poster_url or "",
        runtime=row.runtime,
        seasons_count=row.seasons_count,
        episodes_count=row.episodes_count,
    )


def to_genre(row: Row) -> Genre:
    return Genre(id=row.id, name=row.name, kind=GenreKind(row.kind))


def to_external_id(row: Row) -> ExternalId:
    return ExternalId(source=IdSource(row.source), value=row.value)


def to_external_rating(row: Row) -> ExternalRating:
    return ExternalRating(
        source=RatingSource(row.source), value=row.value, fetched_at=row.fetched_at
    )


def to_rating(row: Row) -> Rating:
    """Пустая рецензия отдаётся пустой строкой, а не `None`: в интерфейс она
    уехала бы словом «None»."""
    return Rating(
        item_id=row.item_id,
        score=row.score,
        visual=row.visual,
        narrative=row.narrative,
        gameplay=row.gameplay,
        review=row.review or "",
    )


def to_tag(row: Row) -> Tag:
    """Тег в тип границы слоёв.

    Отдаётся именно `Tag`, а не пара чисел и строк: тег уезжает к клиенту двумя
    путями — списком набора и составом карточки, — и под двумя типами клиент
    держал бы одно и то же."""
    return Tag(id=row.id, name=row.name)


def to_credit(row: Row, entity: Entity) -> Credit:
    """Строка титров в тип границы слоёв.

    `Entity` приходит параметром: у людей и студий разные таблицы и разные
    наборы ролей, а порядок в титрах есть только у людей."""
    return Credit(
        name=row.name,
        # Роль возвращается перечислением, а не сырой строкой из базы:
        # `==` у StrEnum истинно и для строки, а `is` и `isinstance` —
        # нет, и два пути чтения разошлись бы молча.
        role=entity.roles(row.role),
        position=row.position if entity.position is not None else None,
        source=Source(row.source) if row.source else None,
        source_id=row.source_id,
    )
