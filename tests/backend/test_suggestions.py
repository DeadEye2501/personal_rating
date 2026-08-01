"""Подсказка при вводе имени: тёзок различают по узнаваемой карточке."""

from datetime import timedelta

from sqlalchemy import insert as core_insert

from backend.model import CompanyRole, PersonRole
from backend.storage.repository.credits import companies, people
from backend.storage.repository.ratings import RatingsRepository
from backend.storage.repository.wishlist import WishlistRepository
from backend.storage.tables import external_rating
from tests.conftest import MOMENT


async def person_with(sessions, name: str, item_ids: list[int]) -> int:
    repository = people(sessions)
    person_id = await repository.create_manual(name)
    for item_id in item_ids:
        await repository.attach(item_id, person_id, PersonRole.DIRECTOR)
    return person_id


async def test_hint_is_the_highest_rated_film(sessions, card):
    """Победитель заводится вторым: будь он первым, тест прошёл бы и при
    порядке по номеру карточки вместо порядка по оценке."""
    meh = await card(source_id="1", title="Довод")
    good = await card(source_id="2", title="Интерстеллар")
    await person_with(sessions, "Кристофер Нолан", [good, meh])

    ratings = RatingsRepository(sessions)
    await ratings.set_score(good, 9.0, now=MOMENT)
    await ratings.set_score(meh, 6.0, now=MOMENT)

    found = await people(sessions).suggest("Кристофер")
    assert [(s.name, s.hint) for s in found] == [("Кристофер Нолан", "Интерстеллар")]


async def test_the_hint_carries_the_card_identifier(sessions, card):
    """При наведении показывается ещё и обложка, а хранилище постеров
    ключуется по item_id: по названию его не запросить."""
    only = await card(title="Интерстеллар")
    person_id = await person_with(sessions, "Кристофер Нолан", [only])

    found = await people(sessions).suggest("Кристофер")
    assert (found[0].entity_id, found[0].hint_item_id) == (person_id, only)


async def test_aggregator_scores_do_not_count(sessions, card):
    """Узнают человека по тому, что он значит для тебя, а не для IMDb.

    Чужая оценка и выше, и стоит на карточке, заведённой первой: отвечай
    подсказка хоть по агрегатору, хоть по номеру карточки — вышел бы
    «Дюнкерк»."""
    theirs = await card(source_id="1", title="Дюнкерк")
    mine = await card(source_id="2", title="Наш выпускной")
    await person_with(sessions, "Василий Пупкин", [mine, theirs])
    await RatingsRepository(sessions).set_score(mine, 7.0, now=MOMENT)

    async with sessions() as session:
        await session.execute(
            core_insert(external_rating).values(
                item_id=theirs, source="imdb", value=9.5, fetched_at=MOMENT
            )
        )
        await session.commit()

    found = await people(sessions).suggest("Василий")
    assert found[0].hint == "Наш выпускной"


async def test_without_ratings_the_hint_is_the_freshest_wish(sessions, card):
    older = await card(source_id="1", title="Старое желание")
    newer = await card(source_id="2", title="Свежее желание")
    await person_with(sessions, "Андрей Тарковский", [older, newer])

    wishes = WishlistRepository(sessions)
    await wishes.add(older, now=MOMENT)
    await wishes.add(newer, now=MOMENT + timedelta(days=1))

    found = await people(sessions).suggest("Андрей")
    assert found[0].hint == "Свежее желание"


async def test_a_rated_film_beats_a_wished_one(sessions, card):
    """Оценённый заводится вторым: первым он победил бы и по номеру."""
    wished = await card(source_id="1", title="Отложенный")
    rated = await card(source_id="2", title="Оценённый")
    await person_with(sessions, "Кто-то", [rated, wished])

    await RatingsRepository(sessions).set_score(rated, 4.0, now=MOMENT)
    await WishlistRepository(sessions).add(wished, now=MOMENT)

    found = await people(sessions).suggest("Кто")
    assert found[0].hint == "Оценённый"


async def test_a_review_without_a_score_is_not_a_rating(sessions, card):
    """Строка оценки бывает и без самой оценки — с одной рецензией. В «самое
    высоко оценённое» такая карточка не попадает."""
    reviewed = await card(source_id="1", title="Только рецензия")
    wished = await card(source_id="2", title="Отложенный")
    await person_with(sessions, "Ларс фон Триер", [reviewed, wished])

    await RatingsRepository(sessions).set_review(reviewed, "потом", now=MOMENT)
    await WishlistRepository(sessions).add(wished, now=MOMENT)

    found = await people(sessions).suggest("Ларс")
    assert found[0].hint == "Отложенный"


async def test_neither_rated_nor_wished_still_gets_a_hint(sessions, card):
    """Искал «Одиссею», нашлось три фильма, оценил один — остальные два
    остались. Актёр из них обязан быть узнаваем.

    Карточек именно несколько: на одной третья ступень выглядела бы рабочей
    и без ограничения в одну строку, а с ним она поднимает исключение."""
    ids = [await card(source_id=str(n), title=f"Ничем не отмеченный {n}")
           for n in range(3)]
    await person_with(sessions, "Никто", ids)

    found = await people(sessions).suggest("Никто")
    assert found[0].hint_item_id in ids
    assert found[0].hint == f"Ничем не отмеченный {ids.index(found[0].hint_item_id)}"


async def test_a_person_without_any_card_has_an_empty_hint(sessions):
    await people(sessions).create_manual("Только что заведённый")

    found = await people(sessions).suggest("Только")
    assert (found[0].hint, found[0].hint_item_id) == ("", None)


async def test_namesakes_are_told_apart_by_their_hints(sessions, card):
    """Ровно тот случай, ради которого всё это делается."""
    famous = await card(source_id="1", title="Интерстеллар")
    mine = await card(source_id="2", title="Наш выпускной")
    famous_id = await person_with(sessions, "Василий Пупкин", [famous])
    mine_id = await person_with(sessions, "Василий Пупкин", [mine])

    await RatingsRepository(sessions).set_score(famous, 9.0, now=MOMENT)
    await RatingsRepository(sessions).set_score(mine, 5.0, now=MOMENT)

    found = await people(sessions).suggest("Василий")
    # Пара, а не набор: подсказки, обменянные между тёзками, набор не
    # различает — а различать их этот тест и заведён.
    assert {(s.entity_id, s.hint) for s in found} == {
        (famous_id, "Интерстеллар"), (mine_id, "Наш выпускной")
    }


async def test_the_hint_looks_only_at_this_persons_cards(sessions, card):
    """Соседняя карточка чужого человека в подсказку не попадает, даже если
    оценена выше."""
    mine = await card(source_id="1", title="Моя")
    strangers = await card(source_id="2", title="Чужая")
    await person_with(sessions, "Дени Вильнёв", [mine])
    await person_with(sessions, "Другой человек", [strangers])

    await RatingsRepository(sessions).set_score(mine, 3.0, now=MOMENT)
    await RatingsRepository(sessions).set_score(strangers, 10.0, now=MOMENT)

    found = await people(sessions).suggest("Дени")
    assert found[0].hint == "Моя"


async def test_suggest_matches_the_beginning_of_the_name(sessions):
    await people(sessions).create_manual("Кристофер Нолан")
    await people(sessions).create_manual("Дени Вильнёв")

    assert [s.name for s in await people(sessions).suggest("крис")] == [
        "Кристофер Нолан"
    ]
    assert [s.name for s in await people(sessions).suggest("нолан")] == []
    assert len(await people(sessions).suggest("")) == 2


async def test_like_wildcards_typed_by_a_human_are_literal(sessions):
    """Подчёркивание и процент — обычные знаки имени, а не подстановки."""
    await people(sessions).create_manual("И_ван")
    await people(sessions).create_manual("Иван")

    assert [s.name for s in await people(sessions).suggest("И_")] == ["И_ван"]
    assert await people(sessions).suggest("%") == []


async def test_suggest_respects_the_limit_and_keeps_the_order(sessions):
    """Заводятся с конца: порядок по имени тогда не совпадает с порядком по
    номеру, и предел берёт первых по алфавиту, а не первых записанных."""
    for index in reversed(range(5)):
        await people(sessions).create_manual(f"Человек {index}")

    found = await people(sessions).suggest("Человек", limit=3)
    assert [s.name for s in found] == ["Человек 0", "Человек 1", "Человек 2"]


async def test_the_next_portion_starts_where_the_previous_ended(sessions):
    """Подсказка догружается прокруткой, и порции не должны ни перекрываться,
    ни пропускать людей между собой.

    Заводятся с конца по той же причине, что и у предела: при записи по порядку
    смещение по алфавиту совпало бы со смещением по номеру строки."""
    for index in reversed(range(5)):
        await people(sessions).create_manual(f"Человек {index}")

    first = await people(sessions).suggest("Человек", limit=2)
    second = await people(sessions).suggest("Человек", limit=2, offset=2)

    assert [s.name for s in first] == ["Человек 0", "Человек 1"]
    assert [s.name for s in second] == ["Человек 2", "Человек 3"]


async def test_a_portion_past_the_end_is_empty_not_a_repeat(sessions):
    """Кончились строки — приезжает пустота, по ней страница и перестаёт
    спрашивать. Смещение за конец, отданное с начала, крутило бы список
    бесконечно."""
    await people(sessions).create_manual("Единственный")

    assert await people(sessions).suggest("Единственный", offset=1) == []


async def test_studios_are_suggested_the_same_way(sessions, card):
    """Для приложения эти две сущности почти неразличимы."""
    game = await card(title="Ведьмак")
    studio = await companies(sessions).create("CD Projekt RED")
    await companies(sessions).attach(game, studio, CompanyRole.DEVELOPER)
    await RatingsRepository(sessions).set_score(game, 10.0, now=MOMENT)

    found = await companies(sessions).suggest("CD")
    assert [(s.name, s.hint) for s in found] == [("CD Projekt RED", "Ведьмак")]
