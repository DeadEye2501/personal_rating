"""Пачечное чтение страницы: десять запросов на любое число карточек."""

import pytest
from sqlalchemy import event

from backend.model import (
    CompanyRole,
    ExternalId,
    ExternalRating,
    GenreKind,
    IdSource,
    Kind,
    PersonRole,
    RatingSource,
    Source,
)
from backend.storage.repository.credits import companies, people
from backend.storage.repository.external import (
    ExternalIdsRepository,
    ExternalRatingsRepository,
)
from backend.storage.repository.genres import GenresRepository
from backend.storage.repository.library import LibraryRepository
from backend.storage.repository.ratings import RatingsRepository
from backend.storage.repository.tags import TagsRepository
from backend.storage.repository.tracks import TracksRepository
from backend.storage.repository.views import ViewsRepository
from backend.storage.repository.wishlist import WishlistRepository
from tests.conftest import ACTION, DRAMA, MOMENT, an_item


@pytest.fixture
async def item_id(sessions):
    return await LibraryRepository(sessions).create(
        an_item("157336", "Интерстеллар", year=2014, runtime=169)
    )


async def test_a_bare_card_comes_back(sessions, item_id):
    views = await ViewsRepository(sessions).views_for([item_id])

    view = views[item_id]
    assert (view.item_id, view.title, view.runtime) == (item_id, "Интерстеллар", 169)
    # Ничего на неё не вешали — значит, пусто, а не пустая строка и не ноль.
    assert view.rating is None
    assert (view.tags, view.genres, view.in_wishlist) == ((), (), False)


async def test_an_unknown_identifier_is_simply_absent(sessions, item_id):
    views = await ViewsRepository(sessions).views_for([item_id, 999999])
    assert set(views) == {item_id}


async def test_nothing_is_asked_for_an_empty_list(sessions):
    assert await ViewsRepository(sessions).views_for([]) == {}


async def test_genres_come_with_the_card(sessions, reference, item_id):
    """Жанров два, и по алфавиту они идут не в том порядке, в каком записаны: с
    одним жанром на карточке порядок по имени не наблюдался бы вовсе, а в карточке
    жанры стоят в ряд и перетасовываться между показами не должны."""
    genres = GenresRepository(sessions)
    # «Боевик» — это 1, «Драма» — 3: записываем обратно алфавиту, чтобы
    # сортировка по номеру строки дала другой порядок и была видна.
    await genres.set_for_item(item_id, sorted([DRAMA, ACTION], reverse=True))

    views = await ViewsRepository(sessions).views_for([item_id])

    assert [g.name for g in views[item_id].genres] == ["Боевик", "Драма"]
    assert views[item_id].genres[0].kind is GenreKind.FILM


async def test_tags_come_in_their_manual_order(sessions, item_id):
    tags = TagsRepository(sessions)
    first = await tags.create(Kind.MOVIE, "пересмотреть")
    second = await tags.create(Kind.MOVIE, "с женой")
    await tags.assign(item_id, first)
    await tags.assign(item_id, second)
    await tags.reorder(Kind.MOVIE, [second, first])

    views = await ViewsRepository(sessions).views_for([item_id])

    assert [t.name for t in views[item_id].tags] == ["с женой", "пересмотреть"]


async def test_people_come_in_the_order_of_the_credits(sessions, item_id):
    """Привязываем в обратном порядке: иначе порядок вставки совпал бы с
    порядком в титрах, и потеря order_by осталась бы незамеченной.

    Без position главные роли не отличить от эпизодических, а карточка
    показывает топ-5 актёров."""
    repository = people(sessions)
    for position, name in [(1, "Энн Хэтэуэй"), (0, "Мэттью Макконахи")]:
        entity_id = await repository.create(name)
        await repository.attach(item_id, entity_id, PersonRole.ACTOR, position)

    views = await ViewsRepository(sessions).views_for([item_id])

    assert [c.name for c in views[item_id].people] == [
        "Мэттью Макконахи", "Энн Хэтэуэй"
    ]
    assert [c.position for c in views[item_id].people] == [0, 1]
    assert views[item_id].people[0].role is PersonRole.ACTOR


async def test_studios_come_in_a_stable_order(sessions, item_id):
    """У студий порядка в титрах нет — но и перетасовываться между показами они
    не должны, поэтому порядок задан их собственным номером.

    Привязываем не в том порядке, в каком заводили, и ждём порядок заведения:
    сравнение двух показов между собой сошлось бы при любой реализации, а
    порядок привязки — это то, что вернула бы база и вовсе без сортировки. Имена
    подобраны так, что ожидаемое не совпадает ни с алфавитом, ни с обратным:
    подмена ключа на имя студии тоже краснеет."""
    repository = companies(sessions)
    entities = {}
    for name in ["Warner Bros.", "Legendary", "Syncopy"]:
        entities[name] = await repository.create(name)
    for name in ["Syncopy", "Warner Bros.", "Legendary"]:
        await repository.attach(item_id, entities[name], CompanyRole.PUBLISHER)

    views = await ViewsRepository(sessions).views_for([item_id])

    assert [c.name for c in views[item_id].companies] == [
        "Warner Bros.", "Legendary", "Syncopy"
    ]


async def test_the_identity_of_a_credit_survives_the_page(sessions, item_id):
    """На пути страницы идентичность титров не сторожил никто, только на пути
    репозитория. Перепутанные местами колонки `source` и `source_id` уронили бы
    `Source("525")` на **каждой** карточке ленты с человеком из TMDB — и это
    видно лишь тогда, когда идентичность у человека есть.

    Значения нарочно непохожие: с одинаковыми обмен колонок сошёлся бы."""
    repository = people(sessions)
    entity_id = await repository.create("Кристофер Нолан", Source.TMDB, "525")
    await repository.attach(item_id, entity_id, PersonRole.DIRECTOR)

    credit = (await ViewsRepository(sessions).views_for([item_id]))[item_id].people[0]

    assert (credit.source, credit.source_id) == (Source.TMDB, "525")


async def test_the_row_of_the_person_survives_the_page(sessions, item_id):
    """Клик по имени зовёт `by_entity` именно этим номером, и приходит он к
    клиенту той же дорогой, что и вся страница.

    Номера карточки и человека нарочно разведены лишними людьми: в базе, где у
    обоих первая строка, подмена колонки на `credit.item_id` сходится и молча
    открывает работы случайного человека."""
    repository = people(sessions)
    for number in range(3):
        await repository.create(f"Лишний {number}")
    entity_id = await repository.create("Кристофер Нолан")
    await repository.attach(item_id, entity_id, PersonRole.DIRECTOR)

    credit = (await ViewsRepository(sessions).views_for([item_id]))[item_id].people[0]

    assert credit.entity_id == entity_id
    assert credit.entity_id != item_id


async def test_a_studio_without_identity_comes_back_empty_and_not_broken(
    sessions, item_id
):
    """У студий из магазинов идентичности нет вовсе, и обе колонки пусты. Без
    этой проверки ветка `Source(row.source) if row.source else None` держалась бы
    на честном слове."""
    repository = companies(sessions)
    await repository.attach(item_id, await repository.create("CD Projekt RED"),
                            CompanyRole.DEVELOPER)

    credit = (await ViewsRepository(sessions).views_for([item_id]))[item_id].companies[0]

    assert (credit.source, credit.source_id) == (None, None)


async def test_companies_are_kept_apart_from_people(sessions, item_id):
    repository = companies(sessions)
    entity_id = await repository.create("Syncopy")
    await repository.attach(item_id, entity_id, CompanyRole.PUBLISHER)

    views = await ViewsRepository(sessions).views_for([item_id])

    assert [c.name for c in views[item_id].companies] == ["Syncopy"]
    assert views[item_id].people == ()


async def test_external_ratings_come_with_the_card(sessions, item_id):
    """Пишем в обратном алфавиту порядке: в порядке вставки список сошёлся бы с
    ожидаемым и без сортировки, то есть сторожа бы не было."""
    ratings = ExternalRatingsRepository(sessions)
    await ratings.record(item_id,
                         ExternalRating(RatingSource.METACRITIC, 74.0, MOMENT))
    await ratings.record(item_id, ExternalRating(RatingSource.IMDB, 8.6, MOMENT))

    views = await ViewsRepository(sessions).views_for([item_id])

    # Порядок по имени источника: без него оценки перетасовывались бы между
    # показами, а стоят они в карточке в ряд.
    assert [(r.source, r.value) for r in views[item_id].external] == [
        (RatingSource.IMDB, 8.6), (RatingSource.METACRITIC, 74.0)
    ]


async def test_external_identifiers_come_with_the_card(sessions, item_id):
    """На них собираются ссылки «открыть на IMDb» из карточки."""
    await ExternalIdsRepository(sessions).put(
        item_id, ExternalId(IdSource.IMDB, "tt0816692")
    )

    views = await ViewsRepository(sessions).views_for([item_id])

    assert [(e.source, e.value) for e in views[item_id].external_ids] == [
        (IdSource.IMDB, "tt0816692")
    ]


async def test_an_empty_external_rating_is_still_a_row(sessions, item_id):
    """Пустое значение — это ответ «у источника нет», и лента о нём знает."""
    await ExternalRatingsRepository(sessions).record(
        item_id, ExternalRating(RatingSource.METACRITIC, None, MOMENT)
    )

    views = await ViewsRepository(sessions).views_for([item_id])

    assert views[item_id].external[0].value is None


async def test_my_own_rating_comes_with_the_card(sessions, item_id):
    """У Rating шесть полей, и все с умолчаниями кроме двух: потеря любого
    тихая. У игры так пропали бы все три шкалы."""
    ratings = RatingsRepository(sessions)
    await ratings.set_aspects(item_id, visual=8, narrative=7, gameplay=7,
                              now=MOMENT)
    await ratings.set_review(item_id, "лучшее, что видел", now=MOMENT)

    rating = (await ViewsRepository(sessions).views_for([item_id]))[item_id].rating

    assert (rating.item_id, rating.visual, rating.narrative, rating.gameplay,
            rating.review) == (item_id, 8, 7, 7, "лучшее, что видел")
    assert rating.score == pytest.approx(7.3333, abs=1e-4)


async def test_a_bookmark_is_a_flag(sessions, item_id):
    assert (await ViewsRepository(sessions).views_for([item_id]))[
        item_id
    ].in_wishlist is False

    await WishlistRepository(sessions).add(item_id, now=MOMENT)

    assert (await ViewsRepository(sessions).views_for([item_id]))[
        item_id
    ].in_wishlist is True


async def test_my_marks_do_not_mix_between_cards(sessions, item_id):
    """Главное, что ломается в пачечном чтении: чужие данные в карточке.

    Метка и оценка есть у обеих карточек, но разные: с признаком, который есть
    только у одной, зеленела бы и раскладка всего найденного под один номер.
    Закладок нарочно две из трёх: у всех трёх их не отличить от «стоит у
    кого-то — значит, у всех», а с одной — от «все закладки достались первой
    найденной»."""
    library = LibraryRepository(sessions)
    other_id = await library.create(an_item("27205", "Начало"))
    third_id = await library.create(an_item("577922", "Довод"))

    tags = TagsRepository(sessions)
    mine = await tags.create(Kind.MOVIE, "пересмотреть")
    theirs = await tags.create(Kind.MOVIE, "с женой")
    await tags.assign(item_id, mine)
    await tags.assign(other_id, theirs)

    ratings = RatingsRepository(sessions)
    await ratings.set_score(item_id, 5.0, now=MOMENT)
    await ratings.set_score(other_id, 8.0, now=MOMENT)
    wishlist = WishlistRepository(sessions)
    await wishlist.add(other_id, now=MOMENT)
    await wishlist.add(third_id, now=MOMENT)

    views = await ViewsRepository(sessions).views_for(
        [item_id, other_id, third_id]
    )

    assert [t.name for t in views[item_id].tags] == ["пересмотреть"]
    assert [t.name for t in views[other_id].tags] == ["с женой"]
    assert views[item_id].rating.score == 5.0
    assert views[other_id].rating.score == 8.0
    assert views[item_id].in_wishlist is False
    assert views[other_id].in_wishlist is True
    assert views[third_id].in_wishlist is True


async def test_what_came_from_the_source_does_not_mix_between_cards(
    sessions, reference, item_id
):
    """То же про пять признаков, приехавших снаружи. Разложены так же — по
    одному владельцу на каждый."""
    other_id = await LibraryRepository(sessions).create(an_item("27205", "Начало"))

    genres = GenresRepository(sessions)
    await genres.set_for_item(item_id, [DRAMA])
    await genres.set_for_item(other_id, [ACTION])
    cast, studios = people(sessions), companies(sessions)
    await cast.attach(item_id, await cast.create("Мэттью Макконахи"),
                      PersonRole.ACTOR, 0)
    await studios.attach(item_id, await studios.create("Syncopy"),
                         CompanyRole.PUBLISHER)

    await ExternalRatingsRepository(sessions).record(
        other_id, ExternalRating(RatingSource.IMDB, 8.8, MOMENT)
    )
    await ExternalIdsRepository(sessions).put(
        other_id, ExternalId(IdSource.IMDB, "tt1375666")
    )

    views = await ViewsRepository(sessions).views_for([item_id, other_id])

    assert [g.name for g in views[item_id].genres] == ["Драма"]
    assert [g.name for g in views[other_id].genres] == ["Боевик"]
    assert [c.name for c in views[item_id].people] == ["Мэттью Макконахи"]
    assert views[other_id].people == ()
    assert [c.name for c in views[item_id].companies] == ["Syncopy"]
    assert views[other_id].companies == ()
    assert views[item_id].external == ()
    assert [r.source for r in views[other_id].external] == [RatingSource.IMDB]
    assert views[item_id].external_ids == ()
    assert [e.value for e in views[other_id].external_ids] == ["tt1375666"]


async def test_nothing_comes_back_when_none_of_the_asked_exists(sessions, item_id):
    """Ветка «ни одной из спрошенных карточек нет» — своя: девять запросов на
    признаки для пустого набора никто задавать не должен."""
    assert await ViewsRepository(sessions).views_for([999998, 999999]) == {}


async def test_a_page_costs_the_same_no_matter_how_many_cards(sessions, engine):
    """Ради этого репозиторий и существует: десять запросов на страницу, а не
    десять на карточку. Десять — по числу признаков: сама строка карточки,
    жанры, теги, люди, студии, внешние оценки, внешние идентификаторы, своя
    оценка, закладка и треки.

    Считаем настоящие запросы к базе, а не вызовы внутреннего метода: тот
    вызывается из одного безусловного места, и его счётчик показывал бы единицу
    даже если внутри стоит цикл по карточкам."""
    library = LibraryRepository(sessions)
    one = await library.create(an_item("first", "Первый"))
    many = [await library.create(an_item(str(n), f"Фильм {n}")) for n in range(20)]

    counted = []

    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def count(conn, cursor, statement, parameters, context, executemany):
        counted.append(statement)

    try:
        await ViewsRepository(sessions).views_for([one])
        for_one = len(counted)
        counted.clear()
        views = await ViewsRepository(sessions).views_for(many)
        for_many = len(counted)
        counted.clear()
        await ViewsRepository(sessions).views_for([999999])
        for_none = len(counted)
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", count)

    assert len(views) == 20
    # Десять признаков — десять запросов, и число не растёт с размером порции.
    assert for_one == 10, counted
    assert for_many == for_one
    # Ни одной из спрошенных карточек нет — спрашивать признаки не у кого.
    assert for_none == 1, counted


async def test_an_album_brings_its_tracks_and_a_film_brings_none(sessions, card):
    """Треки едут в показе тем же пачечным чтением, что жанры и состав: без
    этого карточка альбома спрашивала бы их своим запросом на каждую строку
    ленты.

    Порядок наблюдается списком, а не набором: он часть данных, и записан он не
    по алфавиту нарочно.

    Фильм в паре не для симметрии: пустой кортеж у него обязан приехать из
    чтения, а не из умолчания типа — потеряй сборка вызов, оба ответа остались
    бы пустыми и разошлись бы молча только у альбома."""
    album = await card(kind=Kind.MUSIC, source_id="album",
                       title="A Night at the Opera")
    film = await card(kind=Kind.MOVIE, source_id="film", title="Интерстеллар")
    await TracksRepository(sessions).replace(
        album, ["Bohemian Rhapsody", "Love of My Life", "'39"])

    views = await ViewsRepository(sessions).views_for([album, film])

    assert views[album].tracks == ("Bohemian Rhapsody", "Love of My Life", "'39")
    assert views[film].tracks == ()
