"""Люди и студии: одна реализация на две сущности, и различает их идентичность."""

import pytest
from sqlalchemy import text

from backend.model import CompanyRole, Credit, PersonRole, Source
from backend.storage.repository.credits import IdentityTaken, companies, people
from backend.storage.repository.library import LibraryRepository


async def test_roles_are_stored_as_their_plain_values(sessions, engine, card):
    """Роли ложатся в базу текстом и потому часть схемы. Обменяй `DIRECTOR` и
    `ACTOR` местами в перечислении — набор значений не изменится, круговорот
    «записали членом, прочитали членом» сойдётся, а в уже заполненной базе
    режиссёры станут актёрами и раздел «всё с этим человеком» покажет не то.

    Читается сырая колонка: обратное превращение при чтении вернуло бы
    подменённое значение назад и скрыло подмену."""
    item_id = await card()
    person = people(sessions)
    company = companies(sessions)
    await person.attach(item_id, await person.create("Кристофер Нолан"),
                        PersonRole.DIRECTOR)
    await company.attach(item_id, await company.create("Syncopy"),
                         CompanyRole.PUBLISHER)

    async with engine.connect() as connection:
        stored = (
            (await connection.execute(text("SELECT role FROM person_credit"))
             ).scalar_one(),
            (await connection.execute(text("SELECT role FROM company_credit"))
             ).scalar_one(),
        )

    assert stored == ("director", "publisher")


async def test_a_credit_carries_the_row_of_the_person(sessions, card):
    """Клик по имени зовёт поиск по внутреннему идентификатору, а звать его
    нечем без этого поля: имя тёзку не различает, а внешней идентичности у
    половины строк нет.

    Номера карточки и человека разведены лишними людьми: с равными подмена
    колонки на `credit.item_id` сходится и открывает работы чужого."""
    item_id = await card()
    crew = people(sessions)
    for number in range(3):
        await crew.create_manual(f"Лишний {number}")
    entity_id = await crew.create_manual("Кристофер Нолан")
    await crew.attach(item_id, entity_id, PersonRole.DIRECTOR)

    credit = (await crew.credits_of(item_id))[0]
    assert credit.entity_id == entity_id
    assert credit.entity_id != item_id


async def test_the_identity_goes_out_only_when_someone_can_be_asked(sessions):
    """Тройка «имя, внешняя идентичность и её хозяин» — то, чем клик выбирает
    путь наружу. У строки из TMDB идентичность есть, у заведённой руками её нет,
    хотя в базе у неё свой `uuid4` под `manual`: спросить по нему некого.

    Хозяин уезжает наружу с 23.08.2026, и без него номер достался бы чужому
    источнику: человека с карточки фильма можно повесить на книгу руками, а
    номер TMDB, отданный Google, ушёл бы в `inauthor:\"550\"` — без отказа,
    пустой выдачей."""
    repository = people(sessions)
    outer = await repository.create("Кристофер Нолан", Source.TMDB, "525")
    mine = await repository.create_manual("Василий Пупкин")

    assert await repository.identity_of(outer) == ("Кристофер Нолан", "525",
                                                   Source.TMDB)
    assert await repository.identity_of(mine) == ("Василий Пупкин", None,
                                                  Source.MANUAL)
    assert await repository.identity_of(404) is None


async def test_a_studio_may_have_no_identity_at_all(sessions):
    """Steam и GOG отдают названия студий голыми строками — и такая строка
    попадает в безымянные, откуда её потом склеивают по имени."""
    repository = companies(sessions)
    studio = await repository.create("CD Projekt RED")

    assert await repository.find_anonymous_by_name("CD Projekt RED") == studio


async def test_a_manual_person_gets_its_own_identity(sessions, card):
    """Как и ручная карточка: источник `manual`, идентификатор свой. Отсюда и
    следствие — в безымянных он не числится, и склеить его по имени нельзя."""
    item_id = await card()
    repository = people(sessions)
    first = await repository.create_manual("Василий Пупкин")
    second = await repository.create_manual("Василий Пупкин")
    await repository.attach(item_id, first, PersonRole.ACTOR)

    assert first != second
    assert await repository.find_anonymous_by_name("Василий Пупкин") is None
    assert (await repository.credits_of(item_id))[0].source is Source.MANUAL


async def test_two_nameless_namesakes_do_not_break_the_search(sessions):
    """Двое безымянных с одним именем — обычное дело: `create` публичен.
    Отдаётся первый по номеру, а не исключение на две найденные строки."""
    repository = companies(sessions)
    first = await repository.create("Мосфильм")
    await repository.create("Мосфильм")

    assert await repository.find_anonymous_by_name("Мосфильм") == first


async def test_find_by_source_finds_only_the_identified_one(sessions):
    repository = people(sessions)
    await repository.create("Кристофер Нолан")
    identified = await repository.create("Кристофер Нолан", Source.TMDB, "525")

    assert await repository.find_by_source(Source.TMDB, "525") == identified
    assert await repository.find_by_source(Source.TMDB, "999") is None


async def test_one_identity_cannot_belong_to_two_people(sessions):
    """Уникальность (source, source_id) не пробрасывает чужое исключение
    наверх: знание о SQLAlchemy выше слоя данных не поднимается."""
    repository = people(sessions)
    await repository.create("Кристофер Нолан", Source.TMDB, "525")

    with pytest.raises(IdentityTaken):
        await repository.create("Другой Нолан", Source.TMDB, "525")


async def test_ensure_yields_to_the_one_who_inserted_first(sessions):
    """Карточки грузятся разом и делят актёра: между поиском и вставкой
    вставляет сосед, и опоздавший обязан взять чужую строку. Сорвись он —
    писатель откатит карточку целиком, без жанров, состава и оценок.

    Соседняя вставка вклеивается в `create`, а не пускается вперегонки: гонка от
    `gather` наступает не на каждом прогоне, и сторож из неё негодный."""
    repository = people(sessions)
    neighbour = people(sessions)
    credit = Credit("Энди Сёркис", PersonRole.ACTOR,
                    source=Source.TMDB, source_id="1333")
    theirs = None

    original = repository.create

    async def create_after_the_neighbour(name, source=None, source_id=None):
        nonlocal theirs
        repository.create = original
        theirs = await neighbour.create(name, source, source_id)
        return await original(name, source, source_id)

    repository.create = create_after_the_neighbour

    assert await repository.ensure(credit) == theirs
    assert len(await repository.find_by_name("Энди Сёркис")) == 1


async def test_find_by_name_returns_every_namesake(sessions):
    """Совпадение имени само по себе ничего не решает: тёзки существуют,
    и выбирает между ними человек."""
    repository = people(sessions)
    first = await repository.create_manual("Василий Пупкин")
    second = await repository.create("Василий Пупкин", Source.TMDB, "7")

    assert sorted(await repository.find_by_name("василий пупкин")) == sorted(
        [first, second]
    )


async def test_find_anonymous_skips_those_who_have_an_identity(sessions):
    """По имени склеиваем только тех, у кого идентичности нет вовсе."""
    repository = people(sessions)
    await repository.create("Мосфильм", Source.TMDB, "12")
    bare = await repository.create("Мосфильм")

    assert await repository.find_anonymous_by_name("мосфильм") == bare


async def test_find_by_name_ignores_case_and_edge_spaces(sessions):
    """Имя приходит из поля ввода, а туда попадает и лишний пробел."""
    repository = people(sessions)
    found = await repository.create("Андрей Тарковский")
    assert await repository.find_by_name("  АНДРЕЙ ТАРКОВСКИЙ  ") == [found]


async def test_ensure_reuses_the_same_identity(sessions):
    """Один и тот же человек на двух карточках — одна строка, иначе
    «показать всё с этим человеком» разваливается."""
    repository = people(sessions)
    first = await repository.ensure(
        Credit("Кристофер Нолан", PersonRole.DIRECTOR,
               source=Source.TMDB, source_id="525")
    )
    second = await repository.ensure(
        Credit("Кристофер Нолан", PersonRole.ACTOR,
               source=Source.TMDB, source_id="525")
    )
    assert first == second


async def test_ensure_keeps_two_namesakes_from_the_source_apart(sessions):
    """Ровно то, ради чего Credit несёт идентичность: без неё два разных
    актёра с одним именем слились бы молча."""
    repository = people(sessions)
    first = await repository.ensure(
        Credit("Василий Пупкин", PersonRole.ACTOR,
               source=Source.TMDB, source_id="1")
    )
    second = await repository.ensure(
        Credit("Василий Пупкин", PersonRole.ACTOR,
               source=Source.TMDB, source_id="2")
    )
    assert first != second


async def test_ensure_falls_back_to_the_name_without_identity(sessions):
    repository = companies(sessions)
    first = await repository.ensure(Credit("CD Projekt RED", CompanyRole.DEVELOPER))
    second = await repository.ensure(Credit("CD Projekt RED", CompanyRole.PUBLISHER))
    assert first == second


async def test_ensure_does_not_hijack_a_manual_namesake(sessions):
    """Заведённый руками Нолан и приехавший из TMDB — разные строки:
    идентичности у них разные, и присвоить чужую мы не вправе."""
    repository = people(sessions)
    mine = await repository.create_manual("Кристофер Нолан")
    imported = await repository.ensure(
        Credit("Кристофер Нолан", PersonRole.DIRECTOR,
               source=Source.TMDB, source_id="525")
    )
    assert mine != imported


async def test_a_nameless_credit_does_not_stick_to_an_identified_namesake(sessions):
    """Обратный порядок: сначала приехал из источника, потом пришла голая
    строка с тем же именем. Прилипать к чужой идентичности нельзя."""
    repository = companies(sessions)
    identified = await repository.create("Мосфильм", Source.TMDB, "12")
    bare = await repository.ensure(Credit("Мосфильм", CompanyRole.PUBLISHER))
    assert bare != identified


async def test_attach_keeps_the_order_from_the_credits(sessions, card):
    """Порядок берётся из титров, а не из порядка записи и не по алфавиту:
    здесь оба они дали бы обратный ответ."""
    item_id = await card()
    repository = people(sessions)

    matthew = await repository.create("Мэттью Макконахи")
    anne = await repository.create("Энн Хэтэуэй")
    await repository.attach(item_id, matthew, PersonRole.ACTOR, position=1)
    await repository.attach(item_id, anne, PersonRole.ACTOR, position=0)

    found = await repository.credits_of(item_id)
    assert [(c.name, c.position) for c in found] == [
        ("Энн Хэтэуэй", 0), ("Мэттью Макконахи", 1)
    ]


async def test_one_person_can_hold_two_roles_on_one_card(sessions, card):
    """Роль входит в первичный ключ именно поэтому: выпади она оттуда — вторая
    привязка не добавила бы строки, её отбросил бы `on_conflict_do_nothing`, и
    вторая роль исчезла бы молча. У студий это не редкость, а обычный путь: у
    Steam и GOG разработчик и издатель сплошь и рядом одна и та же студия."""
    item_id = await card()
    repository = people(sessions)
    person_id = await repository.create("Клинт Иствуд")

    await repository.attach(item_id, person_id, PersonRole.DIRECTOR)
    await repository.attach(item_id, person_id, PersonRole.ACTOR, position=0)

    roles = {c.role for c in await repository.credits_of(item_id)}
    assert roles == {PersonRole.DIRECTOR, PersonRole.ACTOR}


async def test_attaching_the_same_role_twice_is_quiet(sessions, card):
    item_id = await card()
    repository = people(sessions)
    person_id = await repository.create("Кристофер Нолан")

    await repository.attach(item_id, person_id, PersonRole.DIRECTOR)
    await repository.attach(item_id, person_id, PersonRole.DIRECTOR)

    assert len(await repository.credits_of(item_id)) == 1


async def test_credits_carry_the_identity_back(sessions, card):
    item_id = await card()
    repository = people(sessions)
    person_id = await repository.create("Кристофер Нолан", Source.TMDB, "525")
    await repository.attach(item_id, person_id, PersonRole.DIRECTOR)

    found = (await repository.credits_of(item_id))[0]
    assert (found.source, found.source_id) == (Source.TMDB, "525")
    # Проверяется тип, а не значение: сырое 'director' прошло бы сравнение.
    assert isinstance(found.role, PersonRole)


async def test_credits_of_survives_rows_without_identity(sessions, card):
    item_id = await card()
    repository = companies(sessions)
    studio = await repository.create("CD Projekt RED")
    await repository.attach(item_id, studio, CompanyRole.DEVELOPER)

    found = (await repository.credits_of(item_id))[0]
    assert found.source is None and found.source_id is None


async def test_detach_all_clears_the_card_but_keeps_the_people(sessions, card):
    item_id = await card()
    repository = people(sessions)
    person_id = await repository.create("Кристофер Нолан")
    await repository.attach(item_id, person_id, PersonRole.DIRECTOR)

    await repository.detach_all(item_id)

    assert await repository.credits_of(item_id) == []
    assert await repository.find_by_name("Кристофер Нолан") == [person_id]


async def test_credits_belong_to_their_own_card(sessions, card):
    """И читаются, и снимаются по своей карточке: иначе правка одной стирала
    бы состав соседней молча."""
    mine = await card(source_id="1")
    neighbour = await card(source_id="2")
    repository = people(sessions)
    person_id = await repository.create("Кристофер Нолан")
    await repository.attach(mine, person_id, PersonRole.DIRECTOR)
    await repository.attach(neighbour, person_id, PersonRole.ACTOR)

    await repository.detach_all(mine)

    assert await repository.credits_of(mine) == []
    assert [c.role for c in await repository.credits_of(neighbour)] == [
        PersonRole.ACTOR
    ]


async def test_companies_work_the_same_way(sessions, card):
    """Для приложения эти две сущности почти неразличимы."""
    item_id = await card()
    repository = companies(sessions)

    studio = await repository.create("CD Projekt RED")
    await repository.attach(item_id, studio, CompanyRole.DEVELOPER)

    found = await repository.credits_of(item_id)
    assert [(c.name, c.role) for c in found] == [
        ("CD Projekt RED", CompanyRole.DEVELOPER)
    ]
    assert isinstance(found[0].role, CompanyRole)


async def test_companies_have_no_position(sessions, card):
    """У company_credit колонки position нет — просить её нечем."""
    item_id = await card()
    repository = companies(sessions)
    studio = await repository.create("Мосфильм")

    await repository.attach(item_id, studio, CompanyRole.PUBLISHER, position=3)

    assert (await repository.credits_of(item_id))[0].position is None


async def test_people_and_companies_do_not_share_a_table(sessions, card):
    item_id = await card()
    person_id = await people(sessions).create("Мосфильм")
    await people(sessions).attach(item_id, person_id, PersonRole.DIRECTOR)

    assert await companies(sessions).credits_of(item_id) == []
    assert await companies(sessions).find_by_name("Мосфильм") == []


async def test_deleting_the_card_takes_the_credits_but_not_the_person(
    sessions, card, posters
):
    item_id = await card()
    repository = people(sessions)
    person_id = await repository.create("Кристофер Нолан")
    await repository.attach(item_id, person_id, PersonRole.DIRECTOR)

    await LibraryRepository(sessions).delete(item_id)

    assert await repository.credits_of(item_id) == []
    assert await repository.find_by_name("Кристофер Нолан") == [person_id]
