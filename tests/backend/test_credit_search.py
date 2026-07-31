"""Строка поиска: широкий общий поиск по людям, названию и оригинальному."""

from backend.model import CompanyRole, Kind, PersonRole
from backend.storage.repository.credits import companies, people
from backend.storage.repository.library import LibraryRepository
from tests.builders import an_item


async def test_finds_by_the_name_of_a_person(sessions):
    """Широкий поиск смотрит и на людей: набрал имя — увидел его работы.

    Заглавие модуля: отдельно от соседей он не падает — любая поломка людской
    ветки роняет его вместе с ними. Сторожа у ветки два других, этот описывает.

    Номера карточки и человека разведены лишними людьми, и это не украшение:
    связь склеивается по ссылке на человека, а с равными номерами её подмена на
    номер карточки сходится — поиск начал бы работать по совпадению двух
    несвязанных счётчиков."""
    library = LibraryRepository(sessions)
    crew = people(sessions)
    item_id = await library.create(an_item("1", "Начало"))
    for number in range(3):
        await crew.create_manual(f"Лишний {number}")
    entity_id = await crew.create_manual("Кристофер Нолан")
    await crew.attach(item_id, entity_id, PersonRole.DIRECTOR)

    assert entity_id != item_id
    assert await library.search(Kind.MOVIE, "нолан", limit=20) == [item_id]


async def test_finds_by_the_name_of_a_company(sessions):
    """У игр вместо людей студии, и путь у них тот же. Номера разведены по тому
    же доводу, что и у людей: у студий своя таблица связей и своя ссылка."""
    library = LibraryRepository(sessions)
    studios = companies(sessions)
    item_id = await library.create(an_item("2", "Ведьмак 3", kind=Kind.GAME))
    for number in range(3):
        await studios.create_manual(f"Лишняя {number}")
    entity_id = await studios.create_manual("CD PROJEKT RED")
    await studios.attach(item_id, entity_id, CompanyRole.DEVELOPER)

    assert entity_id != item_id
    assert await library.search(Kind.GAME, "projekt", limit=20) == [item_id]


async def test_a_card_is_returned_once_even_with_two_roles(sessions):
    """Один человек бывает и режиссёром, и актёром — это две строки связи и
    одна карточка.

    `distinct` в запросе для этого не нужен и снят: `EXISTS` — предикат, строк
    он не размножает. Тест остаётся сторожем на случай возврата к соединению —
    вот на нём карточка и заняла бы два места."""
    library = LibraryRepository(sessions)
    crew = people(sessions)
    item_id = await library.create(an_item("5", "Ирландец"))
    entity_id = await crew.create_manual("Мартин Скорсезе")
    await crew.attach(item_id, entity_id, PersonRole.DIRECTOR)
    await crew.attach(item_id, entity_id, PersonRole.ACTOR, position=3)

    assert await library.search(Kind.MOVIE, "скорсезе", limit=20) == [item_id]


async def test_the_kind_still_narrows(sessions):
    """Фильм «Ведьмак» и игра «Ведьмак» — разные вещи, и поиск по составу это
    правило не отменяет.

    Тот же отбор проверяет и `test_search_local.py`, но здесь он про приоритет:
    написанный как `kind == kind | _named(...)` вместо запятой, он перестал бы
    сужать именно на ветке состава."""
    library = LibraryRepository(sessions)
    studios = companies(sessions)
    game = await library.create(an_item("2", "Ведьмак 3", kind=Kind.GAME))
    entity_id = await studios.create_manual("CD PROJEKT RED")
    await studios.attach(game, entity_id, CompanyRole.DEVELOPER)

    assert await library.search(Kind.MOVIE, "projekt", limit=20) == []


async def test_a_person_of_another_card_does_not_bring_this_one(sessions):
    """Проверяется привязка, а не наличие строки в таблице: без условия по
    `item_id` в подзапросе нашлась бы любая карточка, пока в базе есть хоть
    один человек с таким именем."""
    library = LibraryRepository(sessions)
    crew = people(sessions)
    theirs = await library.create(an_item("1", "Начало"))
    mine = await library.create(an_item("6", "Одиссея"))
    entity_id = await crew.create_manual("Кристофер Нолан")
    await crew.attach(theirs, entity_id, PersonRole.DIRECTOR)

    found = await library.search(Kind.MOVIE, "нолан", limit=20)
    assert found == [theirs]
    assert mine not in found


async def test_the_register_does_not_count(sessions):
    """Встроенный в SQLite `lower()` кириллицу не понимает — обе стороны идут
    через ту же `fold`, что и названия."""
    library = LibraryRepository(sessions)
    crew = people(sessions)
    item_id = await library.create(an_item("1", "Начало"))
    entity_id = await crew.create_manual("Кристофер Нолан")
    await crew.attach(item_id, entity_id, PersonRole.DIRECTOR)

    assert await library.search(Kind.MOVIE, "НОЛАН", limit=20) == [item_id]


