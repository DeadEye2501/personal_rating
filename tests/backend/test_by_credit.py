"""Всё с этим человеком и с этой студией."""

from backend.model import CompanyRole, Kind, PersonRole
from backend.service.library import LibraryService
from backend.storage.repository.credits import companies, people
from backend.storage.repository.views import ViewsRepository
from tests.conftest import rated


async def test_everything_of_one_person_comes_back(sessions):
    """У второго человека свой фильм, и он тоже в связях: без него снятый отбор
    по человеку прошёл бы молча — соединение с таблицей связей само отсекает
    карточки, у которых связей нет вовсе."""
    repository = people(sessions)
    nolan = await repository.create("Кристофер Нолан")
    villeneuve = await repository.create("Дени Вильнёв")
    his_id = await rated(sessions, "1", 9.0, title="Интерстеллар")
    hers_id = await rated(sessions, "2", 8.0, title="Дюна")
    unrelated_id = await rated(sessions, "3", 7.0, title="Ничей фильм")
    await repository.attach(his_id, nolan, PersonRole.DIRECTOR)
    await repository.attach(hers_id, villeneuve, PersonRole.DIRECTOR)

    found = await repository.items_of(nolan, Kind.MOVIE)

    assert found == [his_id]
    assert hers_id not in found
    assert unrelated_id not in found


async def test_the_highest_rated_comes_first(sessions):
    repository = people(sessions)
    nolan = await repository.create("Кристофер Нолан")
    weaker_id = await rated(sessions, "1", 6.0, title="Довод")
    stronger_id = await rated(sessions, "2", 9.0, title="Интерстеллар")
    for item_id in (weaker_id, stronger_id):
        await repository.attach(item_id, nolan, PersonRole.DIRECTOR)

    assert await repository.items_of(nolan, Kind.MOVIE) == [
        stronger_id, weaker_id
    ]


async def test_the_unrated_follow_the_rated(sessions):
    """Неоценённое — не мусор: до него просто не дошли руки."""
    repository = people(sessions)
    nolan = await repository.create("Кристофер Нолан")
    unrated_id = await rated(sessions, "1", None, title="Не смотрел")
    rated_id = await rated(sessions, "2", 9.0, title="Интерстеллар")
    for item_id in (unrated_id, rated_id):
        await repository.attach(item_id, nolan, PersonRole.DIRECTOR)

    assert await repository.items_of(nolan, Kind.MOVIE) == [
        rated_id, unrated_id
    ]


async def test_both_roles_of_one_person_give_one_card(sessions):
    """Один человек бывает на карточке и режиссёром, и актёром — карточка от
    этого не удваивается."""
    repository = people(sessions)
    eastwood = await repository.create("Клинт Иствуд")
    item_id = await rated(sessions, "1", 8.0, title="Гран Торино")
    await repository.attach(item_id, eastwood, PersonRole.DIRECTOR)
    await repository.attach(item_id, eastwood, PersonRole.ACTOR)

    assert await repository.items_of(eastwood, Kind.MOVIE) == [item_id]


async def test_the_kind_narrows_and_nothing_else_does(sessions):
    """Вкладка — первичный фильтр, и проверяется он с обеих сторон: сериал того
    же человека во вкладку фильмов не попадает, а во вкладке сериалов он есть.
    Одной стороны мало — зашитый в запрос литерал `MOVIE` проходит её молча.

    Про отсутствие предела тест говорит слабо: пять карточек не отличат «предела
    нет» от `limit=50`. Наблюдаемого следствия у этого свойства нет вовсе, пока
    у человека нет полусотни работ; держится оно тем, что параметра больше не
    существует."""
    repository = people(sessions)
    nolan = await repository.create("Кристофер Нолан")
    films = []
    for number in range(5):
        item_id = await rated(sessions, str(number), 10.0 - number)
        await repository.attach(item_id, nolan, PersonRole.DIRECTOR)
        films.append(item_id)
    series_id = await rated(sessions, "series", 9.5, kind=Kind.SERIES)
    await repository.attach(series_id, nolan, PersonRole.SHOWRUNNER)

    assert await repository.items_of(nolan, Kind.MOVIE) == films
    assert await repository.items_of(nolan, Kind.SERIES) == [series_id]


async def test_studios_work_the_same_way(sessions):
    """Для приложения эти две сущности почти неразличимы."""
    repository = companies(sessions)
    studio = await repository.create("Syncopy")
    item_id = await rated(sessions, "1", 9.0, title="Интерстеллар")
    await repository.attach(item_id, studio, CompanyRole.PUBLISHER)

    assert await repository.items_of(studio, Kind.MOVIE) == [item_id]


async def test_a_studio_does_not_see_the_films_of_a_person(sessions):
    """Номера людей и студий нумеруются порознь, и первый у обоих — единица:
    спроси не ту таблицу связей, и студия получила бы фильмы режиссёра."""
    nolan = await people(sessions).create("Кристофер Нолан")
    studio = await companies(sessions).create("Syncopy")
    item_id = await rated(sessions, "1", 9.0, title="Интерстеллар")
    await people(sessions).attach(item_id, nolan, PersonRole.DIRECTOR)

    assert nolan == studio
    assert await companies(sessions).items_of(studio, Kind.MOVIE) == []


async def test_equal_scores_keep_a_stable_order(sessions):
    """Второй ключ порядка. Без него страницы одного человека могли бы
    перетасовываться между показами: у трилогии оценки нередко совпадают.

    Замерено, чего этот тест стоит: перевёрнутый второй ключ он ловит, а снятый
    — нет. Планировщик и без `ORDER BY` идёт за карточками так, что номера
    выходят по возрастанию; годы против номеров этого не меняют. Ключ остаётся:
    порядок в SQL без `ORDER BY` не обещан вовсе."""
    repository = people(sessions)
    nolan = await repository.create("Кристофер Нолан")
    ids = []
    for number in range(3):
        item_id = await rated(sessions, str(number), 8.0, year=2005 - number)
        await repository.attach(item_id, nolan, PersonRole.DIRECTOR)
        ids.append(item_id)

    assert await repository.items_of(nolan, Kind.MOVIE) == sorted(ids)


async def test_a_person_with_nothing_gives_nothing(sessions):
    repository = people(sessions)
    nobody = await repository.create("Никто")

    assert await repository.items_of(nobody, Kind.MOVIE) == []


async def test_the_cards_come_back_whole(sessions, sections):
    """Лента у этой страницы та же самая — и карточки в ней те же. Порядок
    задаёт запрос по связям, а собирает карточки то же пачечное чтение."""
    feed = LibraryService(sections, ViewsRepository(sessions))
    repository = people(sessions)
    nolan = await repository.create("Кристофер Нолан")
    weaker_id = await rated(sessions, "1", 6.0, title="Довод")
    stronger_id = await rated(sessions, "2", 9.0, title="Интерстеллар")
    for item_id in (weaker_id, stronger_id):
        await repository.attach(item_id, nolan, PersonRole.DIRECTOR)

    ids = await repository.items_of(nolan, Kind.MOVIE)
    views = await feed.views_of(ids)

    assert [view.title for view in views] == ["Интерстеллар", "Довод"]
    assert views[0].rating.score == 9.0
