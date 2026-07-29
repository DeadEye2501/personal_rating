"""Внешние идентификаторы: всё, что не основной источник карточки."""

import pytest

from backend.model import ExternalId, IdSource
from backend.storage.repository.external import (
    ExternalIdsRepository,
    ExternalIdTaken,
)
from backend.storage.repository.library import LibraryRepository


async def test_put_and_read_back(sessions, card):
    item_id = await card()
    repository = ExternalIdsRepository(sessions)

    await repository.put(item_id, ExternalId(IdSource.IMDB, "tt0816692"))

    assert await repository.ids_of(item_id) == [
        ExternalId(IdSource.IMDB, "tt0816692")
    ]


async def test_a_card_may_hold_several_identifiers(sessions, card):
    """Пишутся в обратном алфавиту порядке: иначе объявленный порядок
    выдачи совпал бы с порядком вставки и не проверялся бы ничем."""
    item_id = await card()
    repository = ExternalIdsRepository(sessions)

    await repository.put(item_id, ExternalId(IdSource.KINOPOISK, "258687"))
    await repository.put(item_id, ExternalId(IdSource.IMDB, "tt0816692"))

    assert await repository.ids_of(item_id) == [
        ExternalId(IdSource.IMDB, "tt0816692"),
        ExternalId(IdSource.KINOPOISK, "258687"),
    ]


async def test_the_same_source_is_replaced_not_duplicated(sessions, card):
    """Идентификатор источника у карточки один: приехавший заново заменяет
    прежний, а не ложится рядом."""
    item_id = await card()
    repository = ExternalIdsRepository(sessions)

    await repository.put(item_id, ExternalId(IdSource.IMDB, "tt0000001"))
    await repository.put(item_id, ExternalId(IdSource.IMDB, "tt0816692"))

    assert await repository.ids_of(item_id) == [
        ExternalId(IdSource.IMDB, "tt0816692")
    ]
    assert await repository.find_item(IdSource.IMDB, "tt0000001") is None

    # Обычный путь: карточка обновилась, тот же идентификатор приехал
    # снова. `UNIQUE (source, value)` задет собственной строкой, и это
    # не отказ.
    await repository.put(item_id, ExternalId(IdSource.IMDB, "tt0816692"))
    assert await repository.ids_of(item_id) == [
        ExternalId(IdSource.IMDB, "tt0816692")
    ]


async def test_one_identifier_cannot_belong_to_two_cards(sessions, card):
    """`UNIQUE (source, value)` — бесплатная проверка: один IMDb ID не может
    принадлежать двум карточкам."""
    first = await card(source_id="1")
    second = await card(source_id="2")
    repository = ExternalIdsRepository(sessions)

    await repository.put(first, ExternalId(IdSource.IMDB, "tt0816692"))

    with pytest.raises(ExternalIdTaken):
        await repository.put(second, ExternalId(IdSource.IMDB, "tt0816692"))

    assert await repository.find_item(IdSource.IMDB, "tt0816692") == first


async def test_one_value_may_belong_to_two_different_sources(sessions, card):
    """Уникальность стоит на паре, а не на значении: у игры номер в
    Steam и в GOG совпадает запросто."""
    item_id = await card()
    repository = ExternalIdsRepository(sessions)

    await repository.put(item_id, ExternalId(IdSource.STEAM, "292030"))
    await repository.put(item_id, ExternalId(IdSource.GOG, "292030"))

    assert {i.source for i in await repository.ids_of(item_id)} == {
        IdSource.STEAM, IdSource.GOG
    }


async def test_find_item_by_identifier(sessions, card):
    item_id = await card()
    repository = ExternalIdsRepository(sessions)
    await repository.put(item_id, ExternalId(IdSource.IMDB, "tt0816692"))

    assert await repository.find_item(IdSource.IMDB, "tt0816692") == item_id
    assert await repository.find_item(IdSource.IMDB, "tt0000000") is None
    assert await repository.find_item(IdSource.KINOPOISK, "tt0816692") is None


async def test_identifiers_of_one_card_do_not_leak_into_another(sessions, card):
    first = await card(source_id="1")
    second = await card(source_id="2")
    repository = ExternalIdsRepository(sessions)

    await repository.put(first, ExternalId(IdSource.IMDB, "tt0816692"))

    assert await repository.ids_of(second) == []


async def test_identifiers_go_away_with_the_card(sessions, card, posters):
    item_id = await card()
    repository = ExternalIdsRepository(sessions)
    await repository.put(item_id, ExternalId(IdSource.IMDB, "tt0816692"))

    await LibraryRepository(sessions).delete(item_id, posters)

    assert await repository.find_item(IdSource.IMDB, "tt0816692") is None
