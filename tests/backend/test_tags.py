"""Свои теги: заведение, привязка к карточке и порядок."""

import pytest

from backend.model import Kind
from backend.storage.repository.tags import TagExists, TagsRepository, WrongTagKind


async def test_same_name_in_different_kinds_are_different_tags(sessions):
    """Тег, нужный везде, заводится трижды — это прямое следствие спеки."""
    repository = TagsRepository(sessions)
    movie_tag = await repository.create(Kind.MOVIE, "пересмотреть")
    game_tag = await repository.create(Kind.GAME, "пересмотреть")
    assert movie_tag != game_tag


async def test_duplicate_name_within_one_kind_is_rejected(sessions):
    """Ловим именно `TagExists`, а не `Exception`: на `Exception` тест зеленеет
    от чего угодно, включая опечатку в имени метода."""
    repository = TagsRepository(sessions)
    await repository.create(Kind.MOVIE, "пересмотреть")
    with pytest.raises(TagExists):
        await repository.create(Kind.MOVIE, "пересмотреть")


async def test_a_refused_duplicate_leaves_the_set_as_it_was(sessions):
    """После отказа набор не должен подрасти половиной строки, а следующий тег
    обязан завестись."""
    repository = TagsRepository(sessions)
    await repository.create(Kind.MOVIE, "пересмотреть")
    with pytest.raises(TagExists):
        await repository.create(Kind.MOVIE, "пересмотреть")

    await repository.create(Kind.MOVIE, "переслушать")
    names = [name for _, name in await repository.list_for_kind(Kind.MOVIE)]
    assert names == ["пересмотреть", "переслушать"]


async def test_list_shows_only_the_current_kind(sessions):
    repository = TagsRepository(sessions)
    await repository.create(Kind.MOVIE, "фильмовый")
    await repository.create(Kind.GAME, "игровой")
    names = [name for _, name in await repository.list_for_kind(Kind.MOVIE)]
    assert names == ["фильмовый"]


async def test_a_new_tag_goes_to_the_end_of_its_set(sessions):
    """Новый тег встаёт в конец, а не в начало и не куда попало: нумерация
    продолжается от последней занятой позиции набора."""
    repository = TagsRepository(sessions)
    await repository.create(Kind.MOVIE, "первый")
    await repository.create(Kind.MOVIE, "второй")
    await repository.create(Kind.MOVIE, "третий")

    names = [name for _, name in await repository.list_for_kind(Kind.MOVIE)]
    assert names == ["первый", "второй", "третий"]


async def test_a_new_tag_goes_after_the_reordered_ones(sessions):
    """Конец набора считается по занятым позициям, а не по числу тегов: после
    перестановки заведённый тег обязан встать последним, а не первым.

    Тегов три: на двух позиции 0 и 1, и взятый вместо максимума минимум дал бы
    новому единицу — ничью, которую номер строки разрешил бы в его пользу, и
    подмена прошла бы молча."""
    repository = TagsRepository(sessions)
    first = await repository.create(Kind.MOVIE, "первый")
    second = await repository.create(Kind.MOVIE, "второй")
    third = await repository.create(Kind.MOVIE, "третий")
    await repository.reorder(Kind.MOVIE, [third, first, second])

    await repository.create(Kind.MOVIE, "четвёртый")

    names = [name for _, name in await repository.list_for_kind(Kind.MOVIE)]
    assert names == ["третий", "первый", "второй", "четвёртый"]


async def test_a_new_tag_goes_last_even_after_deletions(sessions):
    """Считать теги вместо позиций — та же ошибка, но заметная только после
    удаления: два тега из трёх сняты, и счёт дал бы новому позицию в середине
    набора."""
    repository = TagsRepository(sessions)
    first = await repository.create(Kind.MOVIE, "первый")
    second = await repository.create(Kind.MOVIE, "второй")
    await repository.create(Kind.MOVIE, "третий")
    await repository.delete(first)
    await repository.delete(second)

    await repository.create(Kind.MOVIE, "четвёртый")

    names = [name for _, name in await repository.list_for_kind(Kind.MOVIE)]
    assert names == ["третий", "четвёртый"]


async def test_reorder_does_not_touch_tags_of_another_set(sessions):
    """Набор в условии перестановки — не украшение: без него порядок чужого
    набора переписывался бы позициями из этого."""
    repository = TagsRepository(sessions)
    game_first = await repository.create(Kind.GAME, "игровой")
    game_second = await repository.create(Kind.GAME, "второй игровой")

    await repository.reorder(Kind.MOVIE, [game_second, game_first])

    names = [name for _, name in await repository.list_for_kind(Kind.GAME)]
    assert names == ["игровой", "второй игровой"]


async def test_lists_give_out_pairs_and_not_rows(sessions, card):
    """Наружу едут пары «номер и имя», а не строки базы: `Row` сравнивается с
    кортежем как равный, и проверка по значениям подмену пропускает."""
    repository = TagsRepository(sessions)
    item_id = await card(Kind.MOVIE)
    await repository.assign(item_id, await repository.create(Kind.MOVIE, "тег"))

    for found in (
        await repository.list_for_kind(Kind.MOVIE),
        await repository.tags_of(item_id),
    ):
        assert [type(one) for one in found] == [tuple]


async def test_manual_order_survives(sessions):
    repository = TagsRepository(sessions)
    first = await repository.create(Kind.MOVIE, "первый")
    second = await repository.create(Kind.MOVIE, "второй")
    third = await repository.create(Kind.MOVIE, "третий")

    await repository.reorder(Kind.MOVIE, [third, first, second])

    names = [name for _, name in await repository.list_for_kind(Kind.MOVIE)]
    assert names == ["третий", "первый", "второй"]


async def test_order_is_independent_per_kind(sessions):
    """В каждом наборе по два тега, и проверяем порядок, а не количество.
    С одним тегом на набор длина равна единице при любом поведении `reorder` —
    такой тест не упадёт, даже если перестановка перенумерует чужой набор."""
    repository = TagsRepository(sessions)
    first = await repository.create(Kind.MOVIE, "фильмовый")
    second = await repository.create(Kind.MOVIE, "второй фильмовый")
    await repository.create(Kind.GAME, "игровой")
    await repository.create(Kind.GAME, "второй игровой")

    await repository.reorder(Kind.MOVIE, [second, first])

    movies = [name for _, name in await repository.list_for_kind(Kind.MOVIE)]
    games = [name for _, name in await repository.list_for_kind(Kind.GAME)]
    assert movies == ["второй фильмовый", "фильмовый"]
    assert games == ["игровой", "второй игровой"]


async def test_assign_and_unassign(sessions, card):
    repository = TagsRepository(sessions)
    item_id = await card(Kind.MOVIE)
    tag_id = await repository.create(Kind.MOVIE, "пересмотреть")

    await repository.assign(item_id, tag_id)
    assert [name for _, name in await repository.tags_of(item_id)] == ["пересмотреть"]

    await repository.unassign(item_id, tag_id)
    assert await repository.tags_of(item_id) == []


async def test_unassign_takes_only_the_asked_pair(sessions, card):
    """Снятие тега с карточки не должно снимать его с остальных и не должно
    снимать с этой карточки остальные."""
    repository = TagsRepository(sessions)
    mine = await card(Kind.MOVIE, "1")
    other = await card(Kind.MOVIE, "2")
    first = await repository.create(Kind.MOVIE, "первый")
    second = await repository.create(Kind.MOVIE, "второй")
    for item_id in (mine, other):
        await repository.assign(item_id, first)
        await repository.assign(item_id, second)

    await repository.unassign(mine, first)

    assert [name for _, name in await repository.tags_of(mine)] == ["второй"]
    assert len(await repository.tags_of(other)) == 2


async def test_tags_of_a_card_are_only_its_own(sessions, card):
    repository = TagsRepository(sessions)
    mine = await card(Kind.MOVIE, "1")
    other = await card(Kind.MOVIE, "2")
    await repository.assign(mine, await repository.create(Kind.MOVIE, "мой"))
    await repository.assign(other, await repository.create(Kind.MOVIE, "чужой"))

    assert [name for _, name in await repository.tags_of(mine)] == ["мой"]


async def test_tags_of_a_card_keep_the_manual_order(sessions, card):
    """Тегов три и порядок нарочно не круговой: на двух любая перестановка
    совпадает с сортировкой по номеру строки, и тест зеленел бы при сортировке
    по чему угодно."""
    repository = TagsRepository(sessions)
    item_id = await card(Kind.MOVIE)
    first = await repository.create(Kind.MOVIE, "первый")
    second = await repository.create(Kind.MOVIE, "второй")
    third = await repository.create(Kind.MOVIE, "третий")
    for tag_id in (first, second, third):
        await repository.assign(item_id, tag_id)

    await repository.reorder(Kind.MOVIE, [third, first, second])

    assert [name for _, name in await repository.tags_of(item_id)] == [
        "третий", "первый", "второй",
    ]


async def test_assigning_twice_is_not_an_error(sessions, card):
    repository = TagsRepository(sessions)
    item_id = await card(Kind.MOVIE)
    tag_id = await repository.create(Kind.MOVIE, "пересмотреть")
    await repository.assign(item_id, tag_id)
    await repository.assign(item_id, tag_id)
    assert len(await repository.tags_of(item_id)) == 1


async def test_foreign_tag_cannot_be_assigned(sessions, card):
    """Репозиторий не даёт повесить тег одного типа на карточку другого.
    Держит это приложение, а не база: item.kind в item_tag нет."""
    repository = TagsRepository(sessions)
    item_id = await card(Kind.MOVIE)
    game_tag = await repository.create(Kind.GAME, "игровой")

    with pytest.raises(WrongTagKind):
        await repository.assign(item_id, game_tag)


async def test_a_refused_assignment_hangs_nothing(sessions, card):
    repository = TagsRepository(sessions)
    item_id = await card(Kind.MOVIE)
    game_tag = await repository.create(Kind.GAME, "игровой")

    with pytest.raises(WrongTagKind):
        await repository.assign(item_id, game_tag)

    assert await repository.tags_of(item_id) == []


async def test_a_tag_that_does_not_exist_cannot_be_assigned(sessions, card):
    repository = TagsRepository(sessions)
    item_id = await card(Kind.MOVIE)
    with pytest.raises(WrongTagKind):
        await repository.assign(item_id, 404)


async def test_a_card_that_does_not_exist_takes_no_tags(sessions):
    """Отказ, а не падение по дороге: без ветки на пустую строку тут вылезет
    `AttributeError` вместо внятного `WrongTagKind`."""
    repository = TagsRepository(sessions)
    tag_id = await repository.create(Kind.MOVIE, "пересмотреть")
    with pytest.raises(WrongTagKind):
        await repository.assign(404, tag_id)


async def test_rename_keeps_the_tag_on_its_cards(sessions, card):
    repository = TagsRepository(sessions)
    item_id = await card(Kind.MOVIE)
    tag_id = await repository.create(Kind.MOVIE, "пересмотреть")
    await repository.assign(item_id, tag_id)

    await repository.rename(tag_id, "переслушать")

    assert [name for _, name in await repository.tags_of(item_id)] == ["переслушать"]


async def test_rename_into_an_occupied_name_is_refused(sessions):
    """Имя занято в этом наборе — отказ, и притом свой: `IntegrityError` из
    SQLAlchemy, пробрось мы его, потащил бы знание о ней вверх по слоям."""
    repository = TagsRepository(sessions)
    first = await repository.create(Kind.MOVIE, "первый")
    await repository.create(Kind.MOVIE, "второй")

    with pytest.raises(TagExists):
        await repository.rename(first, "второй")

    names = [name for _, name in await repository.list_for_kind(Kind.MOVIE)]
    assert names == ["первый", "второй"]


async def test_renaming_into_a_name_from_another_set_is_allowed(sessions):
    """Наборы независимы: «пересмотреть» может быть и у кино, и у игр."""
    repository = TagsRepository(sessions)
    movie_tag = await repository.create(Kind.MOVIE, "фильмовый")
    await repository.create(Kind.GAME, "игровой")

    await repository.rename(movie_tag, "игровой")

    names = [name for _, name in await repository.list_for_kind(Kind.MOVIE)]
    assert names == ["игровой"]


async def test_rename_touches_only_the_asked_tag(sessions):
    repository = TagsRepository(sessions)
    first = await repository.create(Kind.MOVIE, "первый")
    await repository.create(Kind.MOVIE, "второй")

    await repository.rename(first, "переименованный")

    names = [name for _, name in await repository.list_for_kind(Kind.MOVIE)]
    assert names == ["переименованный", "второй"]


async def test_deleting_a_tag_takes_it_out_of_sight(sessions, card):
    """Удалённого тега не видно ни на карточке, ни в наборе. Что при этом
    уходит и строка развески, здесь не проверяется: развеска не видна снаружи
    и без неё, а каскад сторожит `test_tables.py`."""
    repository = TagsRepository(sessions)
    item_id = await card(Kind.MOVIE)
    tag_id = await repository.create(Kind.MOVIE, "пересмотреть")
    await repository.assign(item_id, tag_id)

    await repository.delete(tag_id)

    assert await repository.tags_of(item_id) == []
    assert await repository.list_for_kind(Kind.MOVIE) == []


async def test_deleting_a_tag_takes_only_that_tag(sessions):
    repository = TagsRepository(sessions)
    first = await repository.create(Kind.MOVIE, "первый")
    await repository.create(Kind.MOVIE, "второй")

    await repository.delete(first)

    names = [name for _, name in await repository.list_for_kind(Kind.MOVIE)]
    assert names == ["второй"]
