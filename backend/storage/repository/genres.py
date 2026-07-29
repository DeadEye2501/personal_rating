"""Жанры карточки и разрешение чужих идентификаторов в свои."""

import logging

from sqlalchemy import delete, select
from sqlalchemy.dialects.sqlite import insert

from backend.model import Genre, GenreKind, GenreSource
from backend.storage.repository.base import Repository
from backend.storage.tables import genre as genre_table
from backend.storage.tables import genre_map as genre_map_table
from backend.storage.tables import item_genre as item_genre_table

logger = logging.getLogger(__name__)

# Теговые пространства. Словарь у них открытый и огромный — 432 метки у Steam,
# 203 у GOG, — и большинство жанрами не являются вовсе. Неразмеченный тег это
# норма, а не новость, и в лог он не идёт: иначе на каждой карточке сыпалось бы
# по полтора десятка строк, и настоящее расширение справочника в этом шуме
# никто не заметил бы.
_TAG_SOURCES = frozenset({GenreSource.STEAM_TAG, GenreSource.GOG_TAG})

# Шестнадцать слагов приезжают у GOG в поле `genres`, но жанрами не являются:
# камера, ход времени, эпоха и темы. Это не незнакомое, а известное и
# отвергнутое; не отличив одно от другого, правило перестанет ловить настоящее.
# Список сверяется со спекой машинно — `scripts/genre_map.py`, поэтому он и
# открыт наружу: сверять нечего, если не с чем.
REJECTED_SLUGS = {
    GenreSource.GOG: frozenset({
        "fpp", "tpp", "turnbased", "realtime", "open-world", "exploration",
        "narrative", "fantasy", "scifi", "historical", "modern", "detective",
        "mystery", "comedy", "naval", "educational",
    }),
}


def _is_news(source: GenreSource, ext_id: str) -> bool:
    """Стоит ли говорить об идентификаторе, которого нет в справочнике."""
    if source in _TAG_SOURCES:
        return False
    return ext_id not in REJECTED_SLUGS.get(source, frozenset())


def _to_genre(row) -> Genre:
    return Genre(id=row.id, name=row.name, kind=GenreKind(row.kind))


class GenresRepository(Repository):
    async def resolve(self, source: GenreSource, ext_ids: list[str]) -> list[int]:
        """Внешние идентификаторы в свои. Сборный разворачивается в два,
        незнакомый жанр попадает в лог: имена в справочнике наши, а заводить
        жанр на лету нельзя. Незнакомый тег в лог не идёт — почему, сказано
        у `_TAG_SOURCES`."""
        if not ext_ids:
            return []

        rows = await self._rows(
            select(genre_map_table.c.ext_id, genre_map_table.c.genre_id)
            .where(
                genre_map_table.c.source == source,
                genre_map_table.c.ext_id.in_(ext_ids),
            )
        )

        known: set[str] = set()
        resolved: list[int] = []
        for row in rows:
            known.add(row.ext_id)
            if row.genre_id not in resolved:
                resolved.append(row.genre_id)

        for ext_id in ext_ids:
            if ext_id not in known and _is_news(source, ext_id):
                logger.warning(
                    "неизвестный жанр: источник %s, идентификатор %s", source, ext_id
                )
        return resolved

    async def set_for_item(self, item_id: int, genre_ids: list[int]) -> None:
        """Набор жанров заменяется целиком: пришедшее из источника — это весь
        список, а не добавка к прежнему."""
        cleared = delete(item_genre_table).where(
            item_genre_table.c.item_id == item_id
        )
        if not genre_ids:
            await self._run(cleared)
            return
        await self._run(
            cleared,
            insert(item_genre_table)
            .values([{"item_id": item_id, "genre_id": genre_id}
                     for genre_id in genre_ids])
            .on_conflict_do_nothing(),
        )

    async def genres_of(self, item_id: int) -> list[Genre]:
        return await self._mapped(
            select(genre_table)
            .join(item_genre_table, item_genre_table.c.genre_id == genre_table.c.id)
            .where(item_genre_table.c.item_id == item_id)
            .order_by(genre_table.c.name),
            _to_genre,
        )

    async def list_for_kind(self, kind: GenreKind) -> list[Genre]:
        """Наборов жанров два, и зовут их `film` и `game`, а не `movie` и
        `game`: `Kind.MOVIE`, переданный сюда по ошибке, вернёт пустой список,
        а не киношные жанры."""
        return await self._mapped(
            select(genre_table)
            .where(genre_table.c.kind == kind)
            .order_by(genre_table.c.name),
            _to_genre,
        )
