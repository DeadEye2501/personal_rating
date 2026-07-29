"""Привязка карточки к внешнему источнику: внешнее заполняет только пустое."""

import logging
from dataclasses import replace
from datetime import datetime

from backend.model import Credit, Item, SourceCard
from backend.service.card_parts import CardParts
from backend.service.genres import resolved_genres
from backend.sources.errors import Refusal
from backend.storage.repository.credits import CreditRepository
from backend.storage.repository.library import ItemExists

logger = logging.getLogger(__name__)

# Поля, которые может долить источник. Идентичность, `id` и `synced_at` сюда не
# входят: их ставит сама привязка. Тип содержимого — тоже: что делать со ссылкой
# на сериал у карточки фильма, не решено, и менять его молча нельзя.
_FILLABLE = (
    "title", "original_title", "year", "released_at", "synopsis", "poster_url",
    "runtime", "seasons_count", "episodes_count",
)

_EMPTY = (None, "")


def merge_fields(existing: Item, incoming: Item) -> Item:
    """Внешнее заполняет только пустое. Что человек написал — остаётся его."""
    return replace(existing, **{
        name: getattr(incoming, name)
        for name in _FILLABLE
        if getattr(existing, name) in _EMPTY
    })


def overwrite_fields(existing: Item, incoming: Item) -> Item:
    """Галочка «перезаписать данные» — приехавшее поверх своего, но **только
    приехавшее**. Поле, которого источник не отдал, остаётся как было.

    Подменять карточку объектом источника целиком нельзя: разборщики кладут в
    непришедшие поля пустую строку, а не оставляют их незаполненными. У TMDB с
    `language=ru-RU` пустой `overview` — обычное дело, и написанный руками
    синопсис исчез бы безвозвратно. Для жанров и состава это правило соблюдается
    ниже; здесь оно то же."""
    return replace(existing, **{
        name: getattr(incoming, name)
        for name in _FILLABLE
        if getattr(incoming, name) not in _EMPTY
    })


class Linker(CardParts):
    """Ручная карточка получает источник, а данные человека остаются его."""

    async def link(self, item_id: int, card: SourceCard, now: datetime,
                   overwrite: bool = False) -> None:
        """Поднимает `ItemExists`, если занята идентичность карточки или любой из
        её внешних идентификаторов: это ответ на прямое действие человека, а не
        сбой источника."""
        await self._check_identifiers(item_id, card)

        # Упрёмся здесь и ничего не тронем. Здесь же ставится свежий synced_at:
        # иначе карточка, заведённая полгода назад, сразу окажется просроченной.
        await self._library.link(item_id, card.item.source, card.item.source_id,
                                 now)

        existing = await self._library.get(item_id)
        merge = overwrite_fields if overwrite else merge_fields
        merged = merge(existing, card.item)
        await self._library.replace_fields(item_id, merged)

        await self._fill_genres(item_id, card, overwrite)
        await self._fill(self._people, item_id, card.people, overwrite)
        await self._fill(self._companies, item_id, card.companies, overwrite)

        await self._write_external(item_id, card)

        await self._fill_poster(item_id, merged, overwrite)

    async def _check_identifiers(self, item_id: int, card: SourceCard) -> None:
        """Занятость проверяется целиком и до первой записи: занятый чужой
        карточкой IMDb ID всплыл бы только на записи — то есть после того, как
        источник уже переставлен и поля уже слиты. Карточка осталась бы
        привязанной наполовину, без отката."""
        for external in card.external_ids:
            owner = await self._ids.find_item(external.source, external.value)
            if owner is not None and owner != item_id:
                raise ItemExists(
                    f"{external.source}:{external.value} уже за карточкой {owner}"
                )

    async def _fill_genres(self, item_id: int, card: SourceCard,
                           overwrite: bool) -> None:
        if not overwrite and await self._genres.genres_of(item_id):
            # Выбрал один жанр — набор считается заполненным целиком.
            return
        resolved = await resolved_genres(self._genres, card.genre_ext_ids)
        if resolved:
            # Пустой набор не пишется: источник жанров не отдал или все они
            # незнакомые — стирать свои нечего и незачем. Отдельной проверки на
            # пустой `genre_ext_ids` не нужно, эта её покрывает.
            await self._genres.set_for_item(item_id, resolved)

    async def _fill(self, repository: CreditRepository, item_id: int,
                    credits: tuple[Credit, ...], overwrite: bool) -> None:
        if not credits:
            # У игр состав заполняется только руками — ни Steam, ни GOG людей не
            # отдают. Стереть его перезаписью значит потерять навсегда.
            return
        if not overwrite and await repository.credits_of(item_id):
            # Вписал одного — состав заполнен целиком и не дополняется.
            return
        if overwrite:
            await repository.detach_all(item_id)
        await self._attach_credits(repository, item_id, credits)

    async def _fill_poster(self, item_id: int, item: Item,
                           overwrite: bool) -> None:
        if not overwrite and await self.posters.store.has(item_id):
            return
        poster = await self.posters.fetch(item.source, item.poster_url)
        if isinstance(poster, bytes):
            await self.posters.save(item_id, poster, item.synced_at)
        elif isinstance(poster, Refusal):
            # Карточку не откатываем: строка уже есть, данные уже свои.
            logger.warning("обложка при привязке %s не приехала: %s",
                           item_id, poster.detail)
