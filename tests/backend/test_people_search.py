"""Клик по человеку и студии: внутренняя половина и внешняя."""

import pytest

from backend.model import (
    Found,
    GenreSource,
    Kind,
    Missing,
    PersonHit,
    PersonRole,
    Reason,
    Refusal,
    Source,
)
from backend.service.people import PeopleSearch
from backend.service.search import SearchParts, SearchService
from backend.storage.repository.credits import companies, people
from backend.storage.repository.genres import GenresRepository
from backend.storage.repository.library import LibraryRepository
from backend.storage.repository.removed import RemovedRepository
from backend.storage.repository.views import ViewsRepository
from tests.conftest import FakeSearch, FakeSources, an_item, hit, rated


@pytest.fixture
def parts(sessions):
    return {
        "library": LibraryRepository(sessions),
        "views": ViewsRepository(sessions),
        "people": people(sessions),
        "companies": companies(sessions),
        "parts": SearchParts(genres=GenresRepository(sessions),
                             removed=RemovedRepository(sessions)),
    }


def finder_on(parts, client) -> PeopleSearch:
    """Библиотека сервису не нужна: внутрь он ходит через `items_of` и
    `views_of`, а не через поиск по строке."""
    given = {name: part for name, part in parts.items() if name != "library"}
    return PeopleSearch(sources=FakeSources(client), **given)


async def a_person(parts, name="Кристофер Нолан", source_id=None) -> int:
    """Строка человека в базе. С внешней идентичностью или без неё — этим два
    пути и различаются."""
    if source_id is None:
        return await parts["people"].create_manual(name)
    return await parts["people"].create(name, Source.TMDB, source_id)


def outside_questions(asked: list[tuple]) -> list[tuple]:
    """Только вопросы про людей: у строки поиска есть ещё и запрос по названию,
    а сравнивается тут внешняя половина человека."""
    return [one for one in asked if one[0] in {"find_people", "credits_of"}]


async def test_an_identified_person_is_asked_by_identifier(parts):
    """У человека из TMDB идентификатор уже в базе: спрашивать его по имени
    значило бы притащить тёзок туда, где их быть не должно."""
    client = FakeSearch(works=Found([]))
    entity_id = await a_person(parts, source_id="525")

    await finder_on(parts, client).by_entity("people", entity_id, Kind.MOVIE)

    assert ("credits_of", "525", Kind.MOVIE) in client.asked
    assert not any(name == "find_people" for name, *_ in client.asked)


async def test_clicking_an_author_goes_by_the_name(parts):
    """У автора Google Books номера нет вовсе — `authors` голые строки, и строка
    заводится безымянной. Путь тот же самый, каким сегодня ищется заведённый
    руками режиссёр: по имени, и тёзки приезжают вместе с ним.

    Поведение клика у книги не отличается от клика у фильма ничем — условие
    пользователя 22.08.2026."""
    client = FakeSearch(works=Found([]), people=Found([PersonHit("Фрэнк Герберт")]),
                        name="google_books")
    entity_id = await a_person(parts, "Фрэнк Герберт")

    await finder_on(parts, client).by_entity("people", entity_id, Kind.BOOK)

    assert ("find_people", "Фрэнк Герберт") in client.asked
    assert ("credits_of", "Фрэнк Герберт", Kind.BOOK) in client.asked


async def test_a_foreign_identifier_never_reaches_a_stranger(parts):
    """Человека с карточки фильма можно повесить на книгу руками: `suggest`
    отбирает людей без оглядки на тип, а `attach` вешает кого угодно куда
    угодно. Отдай его номер книжному клиенту — и номер TMDB уехал бы в
    `inauthor:"550"`; отказа не было бы, Google ответил бы пустой выдачей, и
    клик молча не нашёл бы ничего.

    Проверяется тем, что путь сворачивает на поиск по имени — тот самый, которым
    ищется заведённый руками."""
    client = FakeSearch(works=Found([]), people=Found([PersonHit("Лю Цысинь")]),
                        name="google_books")
    entity_id = await a_person(parts, "Лю Цысинь", source_id="550")

    await finder_on(parts, client).by_entity("people", entity_id, Kind.BOOK)

    assert ("find_people", "Лю Цысинь") in client.asked
    assert ("credits_of", "550", Kind.BOOK) not in client.asked


async def test_an_identifier_of_the_answering_source_is_taken_as_it_is(parts):
    """Обратная половина: если номер принадлежит тому же источнику, который и
    отвечает за людей этого типа, спрашивают по номеру — иначе сравнение
    выродилось бы в «никогда не верить номеру», и клик по актёру TMDB притащил
    бы тёзок."""
    client = FakeSearch(works=Found([]), name="tmdb")
    entity_id = await a_person(parts, source_id="525")

    await finder_on(parts, client).by_entity("people", entity_id, Kind.MOVIE)

    assert ("credits_of", "525", Kind.MOVIE) in client.asked
    assert not any(name == "find_people" for name, *_ in client.asked)


async def test_a_manual_person_is_asked_outside_by_name(parts):
    """Внешней идентичности у заведённого руками нет и присвоить ему чужую мы
    не вправе — снаружи остаётся имя."""
    client = FakeSearch(works=Found([]),
                        people=Found([PersonHit("525")]))
    entity_id = await a_person(parts)

    await finder_on(parts, client).by_entity("people", entity_id, Kind.MOVIE)

    assert ("find_people", "Кристофер Нолан") in client.asked


async def test_an_empty_name_is_not_asked_outside(parts):
    """Пустое имя в базе разрешено, а спросить по нему нечего: запрос ушёл бы
    пустым `query` и вернулся отказом, который нечем объяснить человеку."""
    client = FakeSearch(works=Found([]))
    entity_id = await parts["people"].create_manual("")

    found = await finder_on(parts, client).by_entity("people", entity_id,
                                                     Kind.MOVIE)

    assert client.asked == []
    assert found.refusals == ()


async def test_every_namesake_brings_all_their_work(parts):
    """Тёзок находится несколько, и фильмография спрашивается у каждого целиком:
    иначе «все, кого зовут так» отдавало бы работы одного случайного — или по
    одной работе от каждого."""
    client = FakeSearch(
        works={"525": Found([hit("1"), hit("3")]), "999": Found([hit("2")])},
        people=Found([PersonHit("525"), PersonHit("999")]),
    )
    entity_id = await a_person(parts)

    found = await finder_on(parts, client).by_entity("people", entity_id,
                                                     Kind.MOVIE)

    asked_ids = {one[1] for one in client.asked if one[0] == "credits_of"}
    assert asked_ids == {"525", "999"}
    # Список, а не множество: работы одного человека идут подряд, и перемешай
    # их сборка — набор этого не различит, а лента перетасуется.
    assert [view.source_id for view in found.views] == ["1", "3", "2"]


async def test_a_removed_row_does_not_come_back_through_a_click(parts):
    """Убранное человеком не возвращается **никаким** жестом.

    Внешнюю выдачу производят двое — строка поиска и клик по человеку, — и
    инвариант выписан дословно в докстринге `without_removed`: разойдись они,
    удалённое возвращалось бы одним жестом и не возвращалось другим. Сторожила
    его до сих пор только половина строки поиска; снятие отсева здесь оставляло
    весь набор зелёным."""
    client = FakeSearch(works=Found([hit("1"), hit("2")]))
    entity_id = await a_person(parts, source_id="525")
    await parts["parts"].removed.remember(
        an_item("2", "Убранная", kind=Kind.MOVIE, source=Source.TMDB)
    )

    found = await finder_on(parts, client).by_entity("people", entity_id,
                                                     Kind.MOVIE)

    assert [view.source_id for view in found.views] == ["1"]


async def test_the_works_carry_genres_and_the_free_rating(parts, reference):
    """Кандидат клика проходит ту же сборку, что и кандидат строки поиска, —
    со справочником жанров и с бесплатной оценкой источника.

    Без этого фильтр по жанру спрятал бы всю внешнюю половину клика, и выглядело
    бы это как «у режиссёра ничего нет»."""
    client = FakeSearch(works=Found([
        hit(genre_ext_ids=((GenreSource.TMDB, "18"),), source_rating=8.4)
    ]))
    entity_id = await a_person(parts, source_id="525")

    found = await finder_on(parts, client).by_entity("people", entity_id,
                                                     Kind.MOVIE)

    assert [one.name for one in found.views[0].genres] == ["Драма"]
    assert [one.value for one in found.views[0].external] == [8.4]


async def test_nobody_with_such_a_name_outside_is_not_a_refusal(parts):
    """`Missing` — это пустая выдача, а не отказ. Уехав в `refusals`, он свалил
    бы сборку плашки: ни источника, ни причины у него нет."""
    client = FakeSearch(works=Found([]), people=Missing())
    entity_id = await a_person(parts)

    found = await finder_on(parts, client).by_entity("people", entity_id,
                                                     Kind.MOVIE)

    assert found.refusals == ()


async def test_a_refusal_of_the_name_search_is_not_lost(parts):
    """Отказ на первом же шаге — единственное, что отличает «снаружи никого» от
    «спросить не удалось». Потеряв его, выдача из одной своей базы выглядела бы
    полным ответом."""
    client = FakeSearch(
        works=Found([]),
        people=Refusal(source="tmdb", reason=Reason.NETWORK),
    )
    item_id = await parts["library"].create(an_item("11", "Начало"))
    entity_id = await a_person(parts)
    await parts["people"].attach(item_id, entity_id, PersonRole.DIRECTOR)

    found = await finder_on(parts, client).by_entity("people", entity_id,
                                                     Kind.MOVIE)

    assert [view.item_id for view in found.views] == [item_id]
    assert [one.source for one in found.refusals] == ["tmdb"]


async def test_one_source_refuses_once_however_many_it_was_asked(parts):
    """Спросили пятерых, лёг источник — отказ всё равно один: плашка внизу
    говорит про источник, а источник тут один."""
    client = FakeSearch(
        works=Refusal(source="tmdb", reason=Reason.NETWORK),
        people=Found([PersonHit("525"), PersonHit("999")]),
    )
    entity_id = await a_person(parts)

    found = await finder_on(parts, client).by_entity("people", entity_id,
                                                     Kind.MOVIE)

    assert len(found.refusals) == 1


async def test_two_reasons_from_one_source_stay_two(parts):
    """Схлопывание идёт по паре «источник и причина», а не по источнику: у пяти
    найденных один запрос упирается в квоту, другой рвётся по сети, и плашке
    есть что сказать про обе."""
    client = FakeSearch(
        works={"525": Refusal(source="tmdb", reason=Reason.QUOTA),
                 "999": Refusal(source="tmdb", reason=Reason.NETWORK)},
        people=Found([PersonHit("525"), PersonHit("999")]),
    )
    entity_id = await a_person(parts)

    found = await finder_on(parts, client).by_entity("people", entity_id,
                                                     Kind.MOVIE)

    assert {one.reason for one in found.refusals} == {Reason.QUOTA,
                                                      Reason.NETWORK}


async def test_a_person_in_the_game_tab_never_goes_outside(parts):
    """Кого спрашивать — решает реестр, и сервис обязан его слушаться: у игр
    клиента людей нет вовсе. Отдельно от студий, потому что тех отсекает домен,
    ещё до обращения к реестру, — и одной проверкой эти две ветки не различить."""
    client = FakeSearch(works=Found([]))
    entity_id = await a_person(parts)

    found = await finder_on(parts, client).by_entity("people", entity_id,
                                                     Kind.GAME)

    assert client.asked == []
    assert found.refusals == ()


async def test_an_identified_person_in_the_game_tab_never_goes_outside(parts):
    """Тот же вопрос к реестру стоит и на второй ветке — у человека с внешним
    номером. Без него клик в игровой вкладке разыменовал бы клиента, которого
    нет вовсе, и сделал бы это мимо `answered`: там исключение уходит через
    границу потоков."""
    client = FakeSearch(works=Found([]))
    entity_id = await a_person(parts, source_id="525")

    found = await finder_on(parts, client).by_entity("people", entity_id,
                                                     Kind.GAME)

    assert client.asked == []
    assert found.refusals == ()


async def test_a_broken_search_for_people_becomes_a_refusal(parts):
    """Сорвался разбор списка людей — это отказ, а не исключение наружу. Ручка
    зовётся на каждое нажатие Enter в строке поиска, и сорвись она без обёртки,
    исключение ушло бы через границу потоков."""
    client = FakeSearch(people=RuntimeError("разбор не удался"))
    entity_id = await a_person(parts)

    found = await finder_on(parts, client).by_entity("people", entity_id,
                                                     Kind.MOVIE)

    assert [(one.source, one.reason) for one in found.refusals] == [
        ("tmdb", Reason.BROKEN)
    ]


async def test_a_company_never_goes_outside(parts):
    """Внешней половины у студий нет вовсе, и решает это домен, а не вид: у
    киностудии ручки тоже нет, а `/search/person` с названием студии привёз бы
    фильмографию однофамильца. Замер про магазины — в `Sources.people_for`."""
    client = FakeSearch(works=Found([]))
    game_studio = await parts["companies"].create_manual("CD PROJEKT RED")
    film_studio = await parts["companies"].create_manual("Warner Bros.")

    finder = finder_on(parts, client)
    await finder.by_entity("companies", game_studio, Kind.GAME)
    await finder.by_entity("companies", film_studio, Kind.MOVIE)

    assert client.asked == []


async def test_the_inside_half_goes_by_identifier_not_by_name(parts):
    """Внутри идентификатор есть всегда — по нему и кликают. Пойди эта половина
    по имени, клик вернул бы и карточку, которая просто так называется, и
    работы тёзки: то самое, чего клик как раз и не должен."""
    client = FakeSearch(works=Found([]))
    named_alike = await parts["library"].create(an_item("10", "Кристофер Нолан"))
    theirs = await parts["library"].create(an_item("11", "Начало"))
    entity_id = await a_person(parts)
    await parts["people"].attach(theirs, entity_id, PersonRole.DIRECTOR)

    found = await finder_on(parts, client).by_entity("people", entity_id,
                                                     Kind.MOVIE)

    assert [view.item_id for view in found.views] == [theirs]
    assert named_alike not in [view.item_id for view in found.views]


async def test_the_tab_narrows_the_inside_half(parts):
    """Вкладка — первичный фильтр: во вкладке фильмов сериалов не бывает нигде,
    и клик по режиссёру её не отменяет.

    Второе следствие того же: у TMDB фильмы и сериалы нумеруются в независимых
    пространствах, и номера пересекаются. Не сузь своя половина — мой сериал мог
    бы встать на место чужого фильма при склейке."""
    client = FakeSearch(works=Found([]))
    film = await parts["library"].create(an_item("11", "Начало"))
    series = await parts["library"].create(
        an_item("12", "Тёмная материя", kind=Kind.SERIES))
    entity_id = await a_person(parts)
    await parts["people"].attach(film, entity_id, PersonRole.DIRECTOR)
    await parts["people"].attach(series, entity_id, PersonRole.SHOWRUNNER)

    finder = finder_on(parts, client)
    films = await finder.by_entity("people", entity_id, Kind.MOVIE)
    series_only = await finder.by_entity("people", entity_id, Kind.SERIES)

    # Обе стороны, а не только «сериала во вкладке фильмов нет»: с одной
    # зашитый в запрос `MOVIE` вместо вида проходит молча.
    assert [view.item_id for view in films.views] == [film]
    assert [view.item_id for view in series_only.views] == [series]


async def test_all_own_cards_come_in_the_order_of_the_query(parts, sessions):
    """Предела у своей половины нет: вопрос «покажи всё с ним» обрезанным
    ответом не отвечается, а страницы у этого жеста не бывает.

    Порядок при этом задаёт запрос — высокие оценки сверху, — и сервис его не
    трогает: перевернув его по дороге, он показал бы лучшее у человека внизу."""
    client = FakeSearch(works=Found([]))
    entity_id = await a_person(parts)
    theirs = [await rated(sessions, str(n), 7.0 + n, title=f"Работа {n}")
              for n in range(3)]
    for item_id in theirs:
        await parts["people"].attach(item_id, entity_id, PersonRole.DIRECTOR)

    found = await finder_on(parts, client).by_entity("people", entity_id,
                                                     Kind.MOVIE)

    assert [view.item_id for view in found.views] == theirs[::-1]


async def test_own_cards_come_even_when_the_source_refuses(parts):
    """Своя половина от сети не зависит: без неё жест перестал бы работать
    офлайн, а это по правильную сторону главной границы проекта."""
    client = FakeSearch(works=Refusal(source="tmdb", reason=Reason.NETWORK))
    item_id = await parts["library"].create(an_item("11", "Начало"))
    entity_id = await a_person(parts, source_id="525")
    await parts["people"].attach(item_id, entity_id, PersonRole.DIRECTOR)

    found = await finder_on(parts, client).by_entity("people", entity_id,
                                                     Kind.MOVIE)

    assert [view.item_id for view in found.views] == [item_id]
    assert found.refusals


async def test_own_card_wins_over_the_same_one_from_outside(parts):
    """Дубли снимаются по паре «источник + идентификатор», и показывается своё:
    у него есть оценка, теги и закладка."""
    client = FakeSearch(works=Found([hit("27205")]))
    item_id = await parts["library"].create(
        an_item("27205", "Начало"))
    entity_id = await a_person(parts, source_id="525")
    await parts["people"].attach(item_id, entity_id, PersonRole.DIRECTOR)

    found = await finder_on(parts, client).by_entity("people", entity_id,
                                                     Kind.MOVIE)

    same = [view for view in found.views if view.source_id == "27205"]
    assert len(same) == 1
    assert same[0].item_id == item_id


async def test_a_source_that_raises_does_not_break_the_answer(parts):
    """Исключений из сервиса наружу не летит: отказ — значение в результате."""
    class Broken(FakeSearch):
        async def credits_of(self, person_id: str, kind: Kind):
            raise RuntimeError("сломалось")

    entity_id = await a_person(parts, source_id="525")

    found = await finder_on(parts, Broken()).by_entity("people", entity_id,
                                                       Kind.MOVIE)

    assert found.refusals


async def test_an_unknown_entity_has_nothing_to_show(parts):
    """Строки нет — ни своей половины, ни чужой; спрашивать источник не о чем.

    Настоящий человек в базе при этом есть, и спрашиваем мы чужой номер:
    перестань запрос отбирать по нему — вернулась бы пара этого человека, и
    внешняя половина ушла бы в сеть за тем, о ком не спрашивали."""
    client = FakeSearch(works=Found([]))
    await a_person(parts, source_id="525")

    found = await finder_on(parts, client).by_entity("people", 404, Kind.MOVIE)

    assert found.views == ()
    assert client.asked == []


async def test_a_clicked_name_and_a_typed_one_ask_the_same(parts, sessions):
    """Клик по человеку без внешней идентичности и его же имя, набранное в
    строке, — один путь наружу, а не два разошедшихся.

    Разойдись они, обеднела бы молча одна из двух выдач: у клика внешняя
    половина осталась бы без работ тёзок, у строки — без работ вовсе."""
    clicked = FakeSearch(works=Found([hit("1")]),
                         people=Found([PersonHit("525")]))
    typed = FakeSearch(works=Found([hit("1")]),
                       people=Found([PersonHit("525")]))
    entity_id = await a_person(parts)

    await finder_on(parts, clicked).by_entity("people", entity_id, Kind.MOVIE)
    await SearchService(parts["library"], parts["views"], FakeSources(typed),
                        parts["parts"]).external(Kind.MOVIE, "Кристофер Нолан")

    assert outside_questions(clicked.asked) == outside_questions(typed.asked)
    assert outside_questions(typed.asked) != []
