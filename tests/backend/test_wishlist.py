"""Список запланированного: закладка, порядок и порции."""

from datetime import timedelta

from sqlalchemy import select

from backend.storage.repository.wishlist import WishlistRepository
from backend.storage.tables import wishlist as wishlist_table
from tests.conftest import MOMENT as WHEN


async def test_add_and_contains(sessions, card):
    item_id = await card()
    repository = WishlistRepository(sessions)
    assert await repository.contains(item_id) is False
    await repository.add(item_id, now=WHEN)
    assert await repository.contains(item_id) is True


async def test_contains_answers_about_the_asked_card(sessions, card):
    """Без сравнения с `item_id` ответ был бы «да» на любую карточку, стоило
    закладке появиться хоть одной.

    Спрашиваем в обе стороны от закладки, и это не придирка: сравнение легко
    сползает в `>=` или `<=`, а односторонний вопрос такую замену не различает —
    номера у карточек идут по возрастанию, и одна из двух сторон совпадает с
    правильным ответом случайно."""
    lower = await card(source_id="1")
    higher = await card(source_id="2")
    repository = WishlistRepository(sessions)

    await repository.add(lower, now=WHEN)
    assert await repository.contains(higher) is False

    await repository.remove(lower)
    await repository.add(higher, now=WHEN)
    assert await repository.contains(lower) is False


async def test_adding_twice_keeps_the_first_date(sessions, engine, card):
    """Дату проверяем саму, а не через число строк: на порядке в разделе
    «Хочу посмотреть» держится вся его сортировка, а `list_ids` вернёт одну
    строку и тогда, когда `added_at` уехала вперёд."""
    item_id = await card()
    repository = WishlistRepository(sessions)
    await repository.add(item_id, now=WHEN)
    await repository.add(item_id, now=WHEN + timedelta(days=5))

    async with engine.connect() as connection:
        stored = await connection.execute(
            select(wishlist_table.c.added_at).where(
                wishlist_table.c.item_id == item_id
            )
        )
    assert stored.scalar() == WHEN
    assert await repository.list_ids(limit=50, offset=0) == [item_id]


async def test_remove(sessions, card):
    item_id = await card()
    repository = WishlistRepository(sessions)
    await repository.add(item_id, now=WHEN)
    await repository.remove(item_id)
    assert await repository.contains(item_id) is False


async def test_remove_takes_only_the_asked_card(sessions, card):
    mine = await card(source_id="1")
    other = await card(source_id="2")
    repository = WishlistRepository(sessions)
    await repository.add(mine, now=WHEN)
    await repository.add(other, now=WHEN)

    await repository.remove(mine)

    assert await repository.contains(other) is True


async def test_order_is_newest_first(sessions, card):
    """Карточки заводятся в порядке, обратном порядку закладок: совпади они —
    сортировка по дате и сортировка по номеру карточки были бы неразличимы."""
    newer = await card(source_id="2")
    older = await card(source_id="1")
    repository = WishlistRepository(sessions)
    await repository.add(older, now=WHEN)
    await repository.add(newer, now=WHEN + timedelta(days=1))
    assert await repository.list_ids(limit=50, offset=0) == [newer, older]


async def test_the_window_moves_and_never_repeats_a_card(sessions, card):
    """Порция берётся окном: без сдвига вторая страница повторила бы первую."""
    repository = WishlistRepository(sessions)
    identifiers = []
    for number in range(4):
        item_id = await card(source_id=str(number))
        await repository.add(item_id, now=WHEN + timedelta(days=number))
        identifiers.append(item_id)

    newest = list(reversed(identifiers))
    assert await repository.list_ids(limit=2, offset=0) == newest[:2]
    assert await repository.list_ids(limit=2, offset=2) == newest[2:]


async def test_the_list_gives_out_numbers_and_not_rows(sessions, card):
    """Наружу едут номера карточек, а не строки базы."""
    repository = WishlistRepository(sessions)
    await repository.add(await card(), now=WHEN)

    assert [type(one) for one in await repository.list_ids(limit=50, offset=0)] == [int]


async def test_the_order_holds_when_dates_repeat(sessions, card):
    """Закладки, поставленные одной датой, — обычное дело: список наполняют
    пачкой. Без второго ключа сортировки страницы на них разъезжаются."""
    repository = WishlistRepository(sessions)
    identifiers = []
    for number in range(4):
        item_id = await card(source_id=str(number))
        await repository.add(item_id, now=WHEN)
        identifiers.append(item_id)

    first = await repository.list_ids(limit=2, offset=0)
    second = await repository.list_ids(limit=2, offset=2)
    assert first + second == identifiers


async def test_an_empty_wishlist_is_not_an_error(sessions):
    assert await WishlistRepository(sessions).list_ids(limit=50, offset=0) == []
