"""Ручная карточка: заведение, правка и отвязка от источника."""

from datetime import datetime, timedelta

import pytest

from backend.model import Kind, Source, new_manual_item
from backend.storage.repository.library import ItemExists, LibraryRepository
from backend.storage.repository.ratings import RatingsRepository
from tests.conftest import LATER, MOMENT as WHEN


def test_manual_item_gets_its_own_identity():
    first = new_manual_item(Kind.GAME, "Septerra Core", synced_at=WHEN)
    second = new_manual_item(Kind.GAME, "Septerra Core", synced_at=WHEN)

    assert first.source is Source.MANUAL
    assert first.source_id and first.source_id != second.source_id


async def test_only_the_title_is_required(sessions):
    """Карточка с одним названием доезжает до базы и читается обратно —
    сравнение умолчаний датакласса этого не показало бы."""
    repository = LibraryRepository(sessions)
    item_id = await repository.create(new_manual_item(Kind.MOVIE, "Одиссея"))

    stored = await repository.get(item_id)
    assert stored.title == "Одиссея"
    assert stored.year is None
    assert stored.synopsis == ""


async def test_a_manual_card_knows_when_it_was_made(sessions):
    """Время подставляется само и доезжает до базы временем.

    Проверяется кругом через базу, а не полем в памяти: `datetime.now` без
    скобок кладёт в карточку саму функцию, и проверка «не пусто» это
    пропускает — а колонка типа `DateTime` спотыкается уже на записи."""
    repository = LibraryRepository(sessions)
    before = datetime.now()
    item_id = await repository.create(new_manual_item(Kind.MOVIE, "Одиссея"))

    stored = await repository.get(item_id)
    assert isinstance(stored.synced_at, datetime)
    assert stored.synced_at >= before


def test_a_given_moment_is_not_overwritten():
    """Своё время, если его дали: `setdefault`, а не присваивание."""
    item = new_manual_item(Kind.MOVIE, "Одиссея", synced_at=WHEN)
    assert item.synced_at == WHEN


def test_given_fields_reach_the_card():
    item = new_manual_item(Kind.SERIES, "Андор", year=2022, seasons_count=2)
    assert (item.kind, item.title) == (Kind.SERIES, "Андор")
    assert (item.year, item.seasons_count) == (2022, 2)


async def test_manual_card_lands_in_the_library_and_can_be_rated(sessions):
    """Офлайн-обещание целиком: завести руками и поставить оценку."""
    repository = LibraryRepository(sessions)
    item_id = await repository.create(
        new_manual_item(Kind.GAME, "Septerra Core", year=1999, synced_at=WHEN)
    )

    await RatingsRepository(sessions).set_aspects(item_id, 8, 9, 6, now=WHEN)

    stored = await repository.get(item_id)
    assert stored.source is Source.MANUAL
    assert stored.year == 1999
    assert (await RatingsRepository(sessions).get(item_id)).score == pytest.approx(
        7.6667, abs=1e-4
    )


async def test_two_manual_cards_with_the_same_title_both_fit(sessions):
    """Совпадение названия — предупреждение, а не запрет: решает человек."""
    repository = LibraryRepository(sessions)
    first = await repository.create(
        new_manual_item(Kind.MOVIE, "Одиссея", year=1997, synced_at=WHEN)
    )
    second = await repository.create(
        new_manual_item(Kind.MOVIE, "Одиссея", year=2016, synced_at=WHEN)
    )
    assert first != second

    warned = await repository.find_by_title(Kind.MOVIE, "одиссея")
    assert len(warned) == 2


async def test_link_swaps_two_fields_and_keeps_everything_else(sessions):
    repository = LibraryRepository(sessions)
    item_id = await repository.create(
        new_manual_item(Kind.MOVIE, "Интерстеллар", year=2014,
                        synopsis="Мой текст", synced_at=WHEN)
    )
    await RatingsRepository(sessions).set_score(item_id, 9.0, now=WHEN)

    await repository.link(item_id, Source.TMDB, "157336", now=LATER)

    stored = await repository.get(item_id)
    assert stored.id == item_id
    assert stored.source is Source.TMDB
    assert stored.source_id == "157336"
    assert stored.title == "Интерстеллар"
    assert stored.year == 2014
    assert stored.synopsis == "Мой текст"
    # Оценка держится за item.id, а он не менялся.
    assert (await RatingsRepository(sessions).get(item_id)).score == 9.0


async def test_link_takes_only_the_asked_card(sessions):
    repository = LibraryRepository(sessions)
    mine = await repository.create(new_manual_item(Kind.MOVIE, "Мой", synced_at=WHEN))
    other = await repository.create(
        new_manual_item(Kind.MOVIE, "Чужой", synced_at=WHEN)
    )

    await repository.link(mine, Source.TMDB, "157336", now=LATER)

    assert (await repository.get(other)).source is Source.MANUAL


async def test_link_refreshes_synced_at(sessions):
    """Иначе карточка, заведённая давно, в момент привязки сразу окажется
    просроченной и уедет на перезапрос — а там нечего запрашивать.

    Второй момент выводится из первого, а не берётся общей константой: сравняй
    их кто-нибудь, и проверка стала бы тавтологией молча."""
    later = WHEN + timedelta(days=1)
    repository = LibraryRepository(sessions)
    item_id = await repository.create(
        new_manual_item(Kind.MOVIE, "Интерстеллар", synced_at=WHEN)
    )
    await repository.link(item_id, Source.TMDB, "157336", now=later)

    assert (await repository.get(item_id)).synced_at == later


async def test_link_to_an_occupied_identity_is_refused(sessions):
    """Идентичность занята — дубль завести не даём."""
    repository = LibraryRepository(sessions)
    taken = await repository.create(
        new_manual_item(Kind.MOVIE, "Уже есть", synced_at=WHEN)
    )
    await repository.link(taken, Source.TMDB, "157336", now=LATER)

    mine = await repository.create(
        new_manual_item(Kind.MOVIE, "Мой дубль", synced_at=WHEN)
    )
    with pytest.raises(ItemExists):
        await repository.link(mine, Source.TMDB, "157336", now=LATER)

    # Отказ не должен оставить карточку в промежуточном состоянии.
    assert (await repository.get(mine)).source is Source.MANUAL


async def test_unlink_returns_the_card_to_manual_and_keeps_the_data(sessions):
    repository = LibraryRepository(sessions)
    item_id = await repository.create(
        new_manual_item(Kind.MOVIE, "Интерстеллар", year=2014, synced_at=WHEN)
    )
    await repository.link(item_id, Source.TMDB, "157336", now=LATER)

    await repository.unlink(item_id)

    stored = await repository.get(item_id)
    assert stored.source is Source.MANUAL
    assert stored.title == "Интерстеллар"
    assert stored.year == 2014
    # Номер выдаётся свой: чужой, оставшийся в поле, — это карточка, которая
    # называет себя ручной и держит при этом идентификатор TMDB. И он не
    # выводится из номера строки — предсказуемый столкнулся бы с заведённой
    # руками карточкой на ключе уникальности.
    assert stored.source_id not in ("157336", str(item_id))
    # Освободившийся внешний идентификатор снова свободен.
    assert await repository.find_by_source(Kind.MOVIE, Source.TMDB, "157336") is None


async def test_unlink_gives_a_fresh_identity_to_each_card(sessions):
    """Отвязанные карточки не должны столкнуться на одном `source_id`:
    ограничение уникальности не даст завести вторую."""
    repository = LibraryRepository(sessions)
    first = await repository.create(
        new_manual_item(Kind.MOVIE, "Первая", synced_at=WHEN)
    )
    second = await repository.create(
        new_manual_item(Kind.MOVIE, "Вторая", synced_at=WHEN)
    )
    await repository.link(first, Source.TMDB, "1", now=LATER)
    await repository.link(second, Source.TMDB, "2", now=LATER)

    await repository.unlink(first)
    await repository.unlink(second)

    assert (await repository.get(first)).source_id != (
        await repository.get(second)
    ).source_id


async def test_unlink_takes_only_the_asked_card(sessions):
    repository = LibraryRepository(sessions)
    mine = await repository.create(new_manual_item(Kind.MOVIE, "Мой", synced_at=WHEN))
    other = await repository.create(
        new_manual_item(Kind.MOVIE, "Чужой", synced_at=WHEN)
    )
    await repository.link(mine, Source.TMDB, "1", now=LATER)
    await repository.link(other, Source.TMDB, "2", now=LATER)

    await repository.unlink(mine)

    assert (await repository.get(other)).source is Source.TMDB
