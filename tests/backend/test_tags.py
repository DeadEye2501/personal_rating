"""Свои теги: заведение, привязка к карточке и порядок."""

import pytest

from backend.model import Kind, Tag
from backend.storage.repository.tags import TagExists, TagsRepository, WrongTagKind


async def test_same_name_in_different_kinds_are_different_tags(sessions):
    """Тег, нужный везде, заводится трижды — это прямое следствие спеки."""
    repository = TagsRepository(sessions)
    movie_tag = await repository.create(Kind.MOVIE, "Пересмотреть")
    game_tag = await repository.create(Kind.GAME, "Пересмотреть")
    assert movie_tag != game_tag


async def test_duplicate_name_within_one_kind_is_rejected(sessions):
    """Ловим именно `TagExists`, а не `Exception`: на `Exception` тест зеленеет
    от чего угодно, включая опечатку в имени метода."""
    repository = TagsRepository(sessions)
    await repository.create(Kind.MOVIE, "Пересмотреть")
    with pytest.raises(TagExists):
        await repository.create(Kind.MOVIE, "Пересмотреть")


async def test_a_refused_duplicate_leaves_the_set_as_it_was(sessions):
    """После отказа набор не должен подрасти половиной строки, а следующий тег
    обязан завестись."""
    repository = TagsRepository(sessions)
    await repository.create(Kind.MOVIE, "Пересмотреть")
    with pytest.raises(TagExists):
        await repository.create(Kind.MOVIE, "Пересмотреть")

    await repository.create(Kind.MOVIE, "Переслушать")
    names = [tag.name for tag in await repository.list_for_kind(Kind.MOVIE)]
    assert names == ["Пересмотреть", "Переслушать"]


async def test_list_shows_only_the_current_kind(sessions):
    repository = TagsRepository(sessions)
    await repository.create(Kind.MOVIE, "Фильмовый")
    await repository.create(Kind.GAME, "Игровой")
    names = [tag.name for tag in await repository.list_for_kind(Kind.MOVIE)]
    assert names == ["Фильмовый"]


async def test_a_new_tag_goes_to_the_end_of_its_set(sessions):
    """Новый тег встаёт в конец, а не в начало и не куда попало: нумерация
    продолжается от последней занятой позиции набора."""
    repository = TagsRepository(sessions)
    await repository.create(Kind.MOVIE, "Первый")
    await repository.create(Kind.MOVIE, "Второй")
    await repository.create(Kind.MOVIE, "Третий")

    names = [tag.name for tag in await repository.list_for_kind(Kind.MOVIE)]
    assert names == ["Первый", "Второй", "Третий"]


async def test_a_new_tag_goes_after_the_reordered_ones(sessions):
    """Конец набора считается по занятым позициям, а не по числу тегов: после
    перестановки заведённый тег обязан встать последним, а не первым.

    Тегов три: на двух позиции 0 и 1, и взятый вместо максимума минимум дал бы
    новому единицу — ничью, которую номер строки разрешил бы в его пользу, и
    подмена прошла бы молча."""
    repository = TagsRepository(sessions)
    first = await repository.create(Kind.MOVIE, "Первый")
    second = await repository.create(Kind.MOVIE, "Второй")
    third = await repository.create(Kind.MOVIE, "Третий")
    await repository.reorder(Kind.MOVIE, [third, first, second])

    await repository.create(Kind.MOVIE, "Четвёртый")

    names = [tag.name for tag in await repository.list_for_kind(Kind.MOVIE)]
    assert names == ["Третий", "Первый", "Второй", "Четвёртый"]


async def test_a_new_tag_goes_last_even_after_deletions(sessions):
    """Считать теги вместо позиций — та же ошибка, но заметная только после
    удаления: два тега из трёх сняты, и счёт дал бы новому позицию в середине
    набора."""
    repository = TagsRepository(sessions)
    first = await repository.create(Kind.MOVIE, "Первый")
    second = await repository.create(Kind.MOVIE, "Второй")
    await repository.create(Kind.MOVIE, "Третий")
    await repository.delete(first)
    await repository.delete(second)

    await repository.create(Kind.MOVIE, "Четвёртый")

    names = [tag.name for tag in await repository.list_for_kind(Kind.MOVIE)]
    assert names == ["Третий", "Четвёртый"]


async def test_reorder_does_not_touch_tags_of_another_set(sessions):
    """Набор в условии перестановки — не украшение: без него порядок чужого
    набора переписывался бы позициями из этого."""
    repository = TagsRepository(sessions)
    game_first = await repository.create(Kind.GAME, "Игровой")
    game_second = await repository.create(Kind.GAME, "Второй игровой")

    await repository.reorder(Kind.MOVIE, [game_second, game_first])

    names = [tag.name for tag in await repository.list_for_kind(Kind.GAME)]
    assert names == ["Игровой", "Второй игровой"]


async def test_lists_give_out_boundary_tags_and_not_rows(sessions, card):
    """Наружу едет `Tag`, а не строка базы и не пара чисел со строкой: `Row`
    сравнивается с кортежем как равный, и проверка по значениям подмену
    пропускает. Тип один на оба пути — список набора и состав карточки."""
    repository = TagsRepository(sessions)
    item_id = await card(Kind.MOVIE)
    await repository.assign(item_id, await repository.create(Kind.MOVIE, "Тег"))

    for found in (
        await repository.list_for_kind(Kind.MOVIE),
        await repository.tags_of(item_id),
    ):
        assert [type(one) for one in found] == [Tag]


async def test_manual_order_survives(sessions):
    repository = TagsRepository(sessions)
    first = await repository.create(Kind.MOVIE, "Первый")
    second = await repository.create(Kind.MOVIE, "Второй")
    third = await repository.create(Kind.MOVIE, "Третий")

    await repository.reorder(Kind.MOVIE, [third, first, second])

    names = [tag.name for tag in await repository.list_for_kind(Kind.MOVIE)]
    assert names == ["Третий", "Первый", "Второй"]


async def test_order_is_independent_per_kind(sessions):
    """В каждом наборе по два тега, и проверяем порядок, а не количество.
    С одним тегом на набор длина равна единице при любом поведении `reorder` —
    такой тест не упадёт, даже если перестановка перенумерует чужой набор."""
    repository = TagsRepository(sessions)
    first = await repository.create(Kind.MOVIE, "Фильмовый")
    second = await repository.create(Kind.MOVIE, "Второй фильмовый")
    await repository.create(Kind.GAME, "Игровой")
    await repository.create(Kind.GAME, "Второй игровой")

    await repository.reorder(Kind.MOVIE, [second, first])

    movies = [tag.name for tag in await repository.list_for_kind(Kind.MOVIE)]
    games = [tag.name for tag in await repository.list_for_kind(Kind.GAME)]
    assert movies == ["Второй фильмовый", "Фильмовый"]
    assert games == ["Игровой", "Второй игровой"]


async def test_assign_and_unassign(sessions, card):
    repository = TagsRepository(sessions)
    item_id = await card(Kind.MOVIE)
    tag_id = await repository.create(Kind.MOVIE, "Пересмотреть")

    await repository.assign(item_id, tag_id)
    assert [tag.name for tag in await repository.tags_of(item_id)] == ["Пересмотреть"]

    await repository.unassign(item_id, tag_id)
    assert await repository.tags_of(item_id) == []


async def test_unassign_takes_only_the_asked_pair(sessions, card):
    """Снятие тега с карточки не должно снимать его с остальных и не должно
    снимать с этой карточки остальные."""
    repository = TagsRepository(sessions)
    mine = await card(Kind.MOVIE, "1")
    other = await card(Kind.MOVIE, "2")
    first = await repository.create(Kind.MOVIE, "Первый")
    second = await repository.create(Kind.MOVIE, "Второй")
    for item_id in (mine, other):
        await repository.assign(item_id, first)
        await repository.assign(item_id, second)

    await repository.unassign(mine, first)

    assert [tag.name for tag in await repository.tags_of(mine)] == ["Второй"]
    assert len(await repository.tags_of(other)) == 2


async def test_tags_of_a_card_are_only_its_own(sessions, card):
    repository = TagsRepository(sessions)
    mine = await card(Kind.MOVIE, "1")
    other = await card(Kind.MOVIE, "2")
    await repository.assign(mine, await repository.create(Kind.MOVIE, "Мой"))
    await repository.assign(other, await repository.create(Kind.MOVIE, "Чужой"))

    assert [tag.name for tag in await repository.tags_of(mine)] == ["Мой"]


async def test_tags_of_a_card_keep_the_manual_order(sessions, card):
    """Тегов три и порядок нарочно не круговой: на двух любая перестановка
    совпадает с сортировкой по номеру строки, и тест зеленел бы при сортировке
    по чему угодно."""
    repository = TagsRepository(sessions)
    item_id = await card(Kind.MOVIE)
    first = await repository.create(Kind.MOVIE, "Первый")
    second = await repository.create(Kind.MOVIE, "Второй")
    third = await repository.create(Kind.MOVIE, "Третий")
    for tag_id in (first, second, third):
        await repository.assign(item_id, tag_id)

    await repository.reorder(Kind.MOVIE, [third, first, second])

    assert [tag.name for tag in await repository.tags_of(item_id)] == [
        "Третий", "Первый", "Второй",
    ]


async def test_assigning_twice_is_not_an_error(sessions, card):
    repository = TagsRepository(sessions)
    item_id = await card(Kind.MOVIE)
    tag_id = await repository.create(Kind.MOVIE, "Пересмотреть")
    await repository.assign(item_id, tag_id)
    await repository.assign(item_id, tag_id)
    assert len(await repository.tags_of(item_id)) == 1


async def test_foreign_tag_cannot_be_assigned(sessions, card):
    """Репозиторий не даёт повесить тег одного типа на карточку другого.
    Держит это приложение, а не база: item.kind в item_tag нет."""
    repository = TagsRepository(sessions)
    item_id = await card(Kind.MOVIE)
    game_tag = await repository.create(Kind.GAME, "Игровой")

    with pytest.raises(WrongTagKind):
        await repository.assign(item_id, game_tag)


async def test_a_refused_assignment_hangs_nothing(sessions, card):
    repository = TagsRepository(sessions)
    item_id = await card(Kind.MOVIE)
    game_tag = await repository.create(Kind.GAME, "Игровой")

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
    tag_id = await repository.create(Kind.MOVIE, "Пересмотреть")
    with pytest.raises(WrongTagKind):
        await repository.assign(404, tag_id)


async def test_rename_keeps_the_tag_on_its_cards(sessions, card):
    repository = TagsRepository(sessions)
    item_id = await card(Kind.MOVIE)
    tag_id = await repository.create(Kind.MOVIE, "Пересмотреть")
    await repository.assign(item_id, tag_id)

    await repository.rename(tag_id, "Переслушать")

    assert [tag.name for tag in await repository.tags_of(item_id)] == ["Переслушать"]


async def test_rename_into_an_occupied_name_is_refused(sessions):
    """Имя занято в этом наборе — отказ, и притом свой: `IntegrityError` из
    SQLAlchemy, пробрось мы его, потащил бы знание о ней вверх по слоям."""
    repository = TagsRepository(sessions)
    first = await repository.create(Kind.MOVIE, "Первый")
    await repository.create(Kind.MOVIE, "Второй")

    with pytest.raises(TagExists):
        await repository.rename(first, "Второй")

    names = [tag.name for tag in await repository.list_for_kind(Kind.MOVIE)]
    assert names == ["Первый", "Второй"]


async def test_renaming_into_a_name_from_another_set_is_allowed(sessions):
    """Наборы независимы: «пересмотреть» может быть и у кино, и у игр."""
    repository = TagsRepository(sessions)
    movie_tag = await repository.create(Kind.MOVIE, "Фильмовый")
    await repository.create(Kind.GAME, "Игровой")

    await repository.rename(movie_tag, "Игровой")

    names = [tag.name for tag in await repository.list_for_kind(Kind.MOVIE)]
    assert names == ["Игровой"]


async def test_rename_touches_only_the_asked_tag(sessions):
    repository = TagsRepository(sessions)
    first = await repository.create(Kind.MOVIE, "Первый")
    await repository.create(Kind.MOVIE, "Второй")

    await repository.rename(first, "Переименованный")

    names = [tag.name for tag in await repository.list_for_kind(Kind.MOVIE)]
    assert names == ["Переименованный", "Второй"]


async def test_deleting_a_tag_takes_it_out_of_sight(sessions, card):
    """Удалённого тега не видно ни на карточке, ни в наборе. Что при этом
    уходит и строка развески, здесь не проверяется: развеска не видна снаружи
    и без неё, а каскад сторожит `test_tables.py`."""
    repository = TagsRepository(sessions)
    item_id = await card(Kind.MOVIE)
    tag_id = await repository.create(Kind.MOVIE, "Пересмотреть")
    await repository.assign(item_id, tag_id)

    await repository.delete(tag_id)

    assert await repository.tags_of(item_id) == []
    assert await repository.list_for_kind(Kind.MOVIE) == []


async def test_a_tag_knows_how_many_cards_wear_it(sessions, card):
    """Удаление тега спрашивает подтверждение и называет число носителей, а
    ничей тег уходит молча — значит число надо откуда-то взять."""
    repository = TagsRepository(sessions)
    tag_id = await repository.create(Kind.MOVIE, "Пересмотреть")
    lonely = await repository.create(Kind.MOVIE, "Ничей")
    for number in range(3):
        await repository.assign(await card(Kind.MOVIE, source_id=str(number)),
                                tag_id)

    assert await repository.usage(tag_id) == 3
    assert await repository.usage(lonely) == 0


async def test_the_count_is_of_that_tag_and_not_of_all(sessions, card):
    """Считаются носители спрошенного тега, а не строки развески вообще: с
    подсчётом всей таблицы число совпадало бы, пока тег в базе один."""
    repository = TagsRepository(sessions)
    asked = await repository.create(Kind.MOVIE, "Пересмотреть")
    other = await repository.create(Kind.MOVIE, "Шедевр")
    first = await card(Kind.MOVIE, source_id="1")
    second = await card(Kind.MOVIE, source_id="2")
    await repository.assign(first, asked)
    await repository.assign(first, other)
    await repository.assign(second, other)

    assert await repository.usage(asked) == 1


async def test_deleting_a_tag_takes_only_that_tag(sessions):
    repository = TagsRepository(sessions)
    first = await repository.create(Kind.MOVIE, "Первый")
    await repository.create(Kind.MOVIE, "Второй")

    await repository.delete(first)

    names = [tag.name for tag in await repository.list_for_kind(Kind.MOVIE)]
    assert names == ["Второй"]
