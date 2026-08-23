"""Как имя пишется у нас: первая буква заглавная, остальное от источника."""

from sqlalchemy import select

from backend.model import (
    Credit,
    Found,
    Kind,
    PersonRole,
    Source,
)
from backend.naming import capitalized
from backend.storage.entity import COMPANIES, PEOPLE
from backend.storage.repository.credits import CreditRepository
from backend.storage.repository.library import LibraryRepository
from backend.storage.repository.ratings import RatingsRepository
from backend.storage.repository.tags import TagsRepository
from backend.storage.repository.tracks import TracksRepository
from backend.storage.tables import company, person, rating, tag, track
from backend.storage.tables import item as item_table
from tests.conftest import MOMENT, FakeSearch, an_item, hit


def test_a_lowercase_name_gets_its_capital():
    """Решение пользователя 23.08.2026. Источник пишет как хочет: у Deezer
    исполнитель «жадный дельфин» и альбом «консумерки» строчными — это его
    стилизация, а у нас всё пишется одинаково."""
    assert capitalized("жадный дельфин") == "Жадный дельфин"
    assert capitalized("консумерки") == "Консумерки"


def test_the_rest_of_the_name_is_left_alone():
    """Поднимается ровно первая буква: остальное — написание источника, и
    трогать его нельзя. «iPhone» посреди названия обязан уцелеть."""
    assert capitalized("не дрочись, iPhone") == "Не дрочись, iPhone"
    assert capitalized("HORROR VACUI") == "HORROR VACUI"


def test_a_name_that_starts_with_a_capital_is_not_touched():
    """Строка возвращается той же, а не пересобранной: пересборка на пустом
    месте меняла бы байты у всех до единого."""
    name = "Группа крови"

    assert capitalized(name) is name


def test_what_has_no_letter_to_raise_survives():
    """Пустая строка, число и знак: у первого символа заглавной формы нет, и
    городить ветку под каждый случай незачем — `upper` вернёт его же."""
    assert capitalized("") == ""
    assert capitalized("12_22") == "12_22"
    assert capitalized("...ещё") == "...ещё"


def test_the_cost_is_named_and_accepted():
    """Правило необратимо портит стилизованное со строчной: `iRacing` станет
    `IRacing`, `iowa` — `Iowa`. Решение пользователя 23.08.2026: поднимать
    всегда. Записано тестом, чтобы следующий читатель не принял это за ошибку."""
    assert capitalized("iRacing") == "IRacing"
    assert capitalized("iowa") == "Iowa"


async def test_a_card_is_stored_with_its_capitals(sessions):
    """Правило стоит на записи, а не на показе: в базе должно лежать то, что
    человек видит. Проверяется на строке базы, а не на возврате — вернуть можно
    и правильное, записав кривое."""
    item_id = await LibraryRepository(sessions).create(an_item(
        "1", "не дрочись", kind=Kind.MUSIC, source=Source.DEEZER,
        original_title="horror vacui", synopsis="альбом жадного дельфина"))

    async with sessions() as session:
        row = (await session.execute(
            select(item_table).where(item_table.c.id == item_id))).one()

    assert row.title == "Не дрочись"
    assert row.original_title == "Horror vacui"
    assert row.synopsis == "Альбом жадного дельфина"


async def test_an_edited_card_is_stored_with_its_capitals_too(sessions):
    """Пятая дверь записи — правка из окна карточки, и правило у неё то же.

    Дверь своя: `replace_fields` пишет все поля разом и `create` не зовёт вовсе.
    Сегодня обе идут через один сборщик значений, но перестань правка его
    звать — и набранное человеком легло бы в базу как набрано, а показано было
    бы как везде. Заметить это можно было бы только глазами."""
    library = LibraryRepository(sessions)
    item_id = await library.create(an_item("1", "Альбом", kind=Kind.MUSIC,
                                           source=Source.DEEZER))

    await library.replace_fields(item_id, an_item(
        "1", "консумерки", kind=Kind.MUSIC, source=Source.DEEZER,
        original_title="horror vacui", synopsis="альбом жадного дельфина"))

    async with sessions() as session:
        row = (await session.execute(
            select(item_table).where(item_table.c.id == item_id))).one()

    assert (row.title, row.original_title) == ("Консумерки", "Horror vacui")
    assert row.synopsis == "Альбом жадного дельфина"


async def test_a_person_a_studio_a_track_and_a_tag_are_stored_the_same_way(sessions):
    """Четыре двери записи, и правило у них одно: разойдись они, «жадный
    дельфин» оказался бы в базе дважды — исполнителем и строчным тёзкой.

    Карточка проверяется соседним тестом, правка тега и рецензия — следующим:
    их двери человек открывает сам, и потерять правило там было бы виднее
    всего."""
    item_id = await LibraryRepository(sessions).create(an_item("1", "Альбом"))
    people = CreditRepository(sessions, PEOPLE)
    studios = CreditRepository(sessions, COMPANIES)
    person_id = await people.ensure(Credit(name="жадный дельфин",
                                           role=PersonRole.PERFORMER))
    company_id = await studios.create("издательство аст")
    await TracksRepository(sessions).replace(item_id, ["ad astrum", "лететь"])
    tag_id = await TagsRepository(sessions).create(Kind.MUSIC, "переслушать")

    async with sessions() as session:
        names = {
            "person": (await session.execute(select(person.c.name).where(
                person.c.id == person_id))).scalar_one(),
            "company": (await session.execute(select(company.c.name).where(
                company.c.id == company_id))).scalar_one(),
            "tag": (await session.execute(select(tag.c.name).where(
                tag.c.id == tag_id))).scalar_one(),
        }
        tracks = [row.title for row in (await session.execute(
            select(track.c.title).where(track.c.item_id == item_id)
            .order_by(track.c.position))).all()]

    assert names == {"person": "Жадный дельфин", "company": "Издательство аст",
                     "tag": "Переслушать"}
    assert tracks == ["Ad astrum", "Лететь"]


async def test_a_renamed_tag_and_a_review_keep_the_rule(sessions):
    """Правку человек пишет сам, и правило её тоже касается: набор тегов
    правится переименованием, а рецензия — единственный длинный текст, который
    в базу кладёт не источник.

    Обе двери сняты ревью 23.08.2026 мутацией при зелёном наборе: сторожей у
    них не было вовсе."""
    tags = TagsRepository(sessions)
    tag_id = await tags.create(Kind.MUSIC, "переслушать")
    await tags.rename(tag_id, "послушать ещё раз")

    item_id = await LibraryRepository(sessions).create(an_item("1", "Альбом"))
    await RatingsRepository(sessions).set_review(item_id, "слушать можно",
                                                 MOMENT)

    async with sessions() as session:
        name = (await session.execute(select(tag.c.name).where(
            tag.c.id == tag_id))).scalar_one()
        review = (await session.execute(select(rating.c.review).where(
            rating.c.item_id == item_id))).scalar_one()

    assert name == "Послушать ещё раз"
    assert review == "Слушать можно"


async def test_a_candidate_of_the_search_is_shown_the_same_way_it_will_be_stored(
    sessions, service
):
    """Строка выдачи ещё не в базе, и правило записи её не касается — а видит её
    человек раньше всего. Разойдись показ с записью, «не дрочись» стало бы
    «Не дрочись» ровно в тот миг, когда карточку завели.

    Спрашивается **выдача сервиса**, а не сама `written`: единственный её боевой
    вызов — строка в `to_views`, и проверка самой функции за потерю этой строки
    упасть не может. Ревью 23.08.2026 сняло её мутацией при зелёном наборе.

    Правило стоит в сервисе, а не в `view_from_hit`: модель по решению проекта
    не зависит ни от чего нашего, и сторож границы это держит."""

    lowercase = hit("1", "не дрочись", kind=Kind.MUSIC, source=Source.DEEZER,
                    original_title="horror vacui",
                    synopsis="альбом жадного дельфина")

    answer = await service(FakeSearch(Found([lowercase]))).external(
        Kind.MUSIC, "не дрочись")

    shown = answer.views[0]
    assert shown.title == "Не дрочись"
    assert shown.original_title == "Horror vacui"
    assert shown.synopsis == "Альбом жадного дельфина"
