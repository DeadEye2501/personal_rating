"""Третий круг: оценки агрегаторов и сроки их годности."""

from datetime import timedelta

import pytest
from sqlalchemy import event

from backend.model import (
    ExternalId,
    ExternalRating,
    Found,
    IdSource,
    Kind,
    Missing,
    RatingSource,
    Ratings,
    Reason,
    Refusal,
    Source,
)
from backend.service.enrich import Enricher
from backend.storage.repository.external import (
    EMPTY_TTL,
    VALUE_TTL,
    ExternalIdsRepository,
    ExternalRatingsRepository,
)
from backend.storage.repository.library import LibraryRepository
from tests.conftest import MOMENT, FakeClient, FakeSources, an_item, ours


class FakeRatings(FakeClient):
    """Оценочный клиент: что он умеет привозить, объявлено списком, как у
    настоящих."""

    def __init__(self, provides, outcome, name: str = "mdblist") -> None:
        super().__init__(outcome, name)
        self.PROVIDES = provides

    async def ratings(self, imdb_id: str, _kind: Kind):
        self.asked.append(imdb_id)
        return self.outcome


class Breaking(FakeRatings):
    """Клиент, падающий не тем, что клиенты ловят: так выглядит наша опечатка или
    чужая библиотека. Провод и разбор клиент разбирает сам и отдаёт отказом."""

    async def ratings(self, imdb_id: str, _kind: Kind):
        self.asked.append(imdb_id)
        raise KeyError("payload")


@pytest.fixture
async def item_id(sessions):
    made = await LibraryRepository(sessions).create(
        an_item("157336", "Интерстеллар")
    )
    await ExternalIdsRepository(sessions).put(
        made, ExternalId(IdSource.IMDB, "tt0816692")
    )
    return made


@pytest.fixture
async def enrich(sessions):
    """Обогатитель с остановленными часами: сроки годности — предмет проверки."""

    def build(*clients) -> Enricher:
        return Enricher(
            sources=FakeSources(*clients),
            ids=ExternalIdsRepository(sessions),
            ratings=ExternalRatingsRepository(sessions),
            clock=lambda: MOMENT,
        )

    return build


def found(*pairs) -> Found:
    return Found(Ratings(values=tuple(
        ExternalRating(source, value, MOMENT) for source, value in pairs
    )))


async def stored_ratings(sessions, item_id) -> dict:
    rows = await ExternalRatingsRepository(sessions).ratings_of(item_id)
    return {row.source: row.value for row in rows}


async def test_a_value_is_written(sessions, item_id, enrich):
    service = enrich(FakeRatings((RatingSource.IMDB,),
                                 found((RatingSource.IMDB, 8.6))))

    await service.enrich(item_id, Kind.MOVIE)

    assert await stored_ratings(sessions, item_id) == {RatingSource.IMDB: 8.6}


async def test_the_state_after_enrichment_comes_back(sessions, item_id, enrich):
    service = enrich(FakeRatings((RatingSource.IMDB,),
                                 found((RatingSource.IMDB, 8.6))))

    result = await service.enrich(item_id, Kind.MOVIE)

    assert [(r.source, r.value) for r in result] == [(RatingSource.IMDB, 8.6)]


async def test_a_missing_answer_becomes_an_empty_row(sessions, item_id, enrich):
    """Второе из трёх состояний: спрашивали, у источника нет."""
    service = enrich(FakeRatings((RatingSource.IMDB,), Missing()))

    await service.enrich(item_id, Kind.MOVIE)

    assert await stored_ratings(sessions, item_id) == {RatingSource.IMDB: None}


async def test_a_source_absent_from_the_answer_becomes_an_empty_row(
    sessions, item_id, enrich
):
    """Нашёл фильм, а метакритика не дал — это тоже «у него нет»."""
    service = enrich(FakeRatings(
        (RatingSource.IMDB, RatingSource.METACRITIC),
        found((RatingSource.IMDB, 8.6)),
    ))

    await service.enrich(item_id, Kind.MOVIE)

    assert await stored_ratings(sessions, item_id) == {
        RatingSource.IMDB: 8.6, RatingSource.METACRITIC: None
    }


async def test_a_refusal_writes_nothing_at_all(sessions, item_id, enrich):
    """Иначе в базе на неделю поселилось бы «у IMDb нет Интерстеллара»."""
    service = enrich(FakeRatings((RatingSource.IMDB,),
                                 Refusal(source="omdb", reason=Reason.QUOTA)))

    await service.enrich(item_id, Kind.MOVIE)

    assert await stored_ratings(sessions, item_id) == {}


async def test_a_broken_client_writes_nothing_either(sessions, item_id, enrich,
                                                    caplog):
    """Сорвавшийся клиент до ответа не дошёл — это отказ, а не «такого нет»."""
    client = FakeRatings((RatingSource.IMDB,), None)

    async def broken(imdb_id, kind):
        raise RuntimeError("разбор не удался")

    client.ratings = broken
    with caplog.at_level("ERROR"):
        await enrich(client).enrich(item_id, Kind.MOVIE)

    assert await stored_ratings(sessions, item_id) == {}
    # Запись обязательна: `caplog` тут был и раньше, но про лог ничего не
    # утверждалось, и замена `logger.exception` на `logger.debug` в
    # `service/asking.py` прошла бы молча.
    assert [r.levelname for r in caplog.records if r.name.startswith("backend")]         == ["ERROR"]
    # Имя сорвавшегося — присутствием своего и отсутствием чужого: у MDBList и
    # OMDB в `PROVIDES` одно и то же `imdb`, и подмена `client.name` на
    # `client.PROVIDES[0]` показала бы в логе оба источника одним. Проект эту
    # регрессию уже имел один раз.
    assert any(message.startswith("mdblist:") for message in ours(caplog))
    assert not any(message.startswith("imdb:") for message in ours(caplog))


async def test_one_refusal_does_not_let_another_source_write_an_empty_row(
    sessions, item_id, enrich
):
    """IMDb знают оба. Один отказал, второй промолчал — пустоту не пишем: мы не
    смогли посмотреть, а не «такого нет»."""
    service = enrich(
        FakeRatings((RatingSource.IMDB,),
                    Refusal(source="omdb", reason=Reason.QUOTA)),
        FakeRatings((RatingSource.IMDB, RatingSource.METACRITIC),
                    found((RatingSource.METACRITIC, 74.0))),
    )

    await service.enrich(item_id, Kind.MOVIE)

    assert await stored_ratings(sessions, item_id) == {
        RatingSource.METACRITIC: 74.0
    }


async def test_a_value_from_one_source_is_not_erased_by_another(
    sessions, item_id, enrich
):
    service = enrich(
        FakeRatings((RatingSource.IMDB,), found((RatingSource.IMDB, 8.6))),
        FakeRatings((RatingSource.IMDB,), Missing()),
    )

    await service.enrich(item_id, Kind.MOVIE)

    assert await stored_ratings(sessions, item_id) == {RatingSource.IMDB: 8.6}


async def test_a_null_in_the_answer_is_an_empty_row(sessions, item_id, enrich):
    """У найденного объекта конкретный рейтинг бывает null — это ответ."""
    service = enrich(FakeRatings((RatingSource.IMDB,),
                                 found((RatingSource.IMDB, None))))

    await service.enrich(item_id, Kind.MOVIE)

    assert await stored_ratings(sessions, item_id) == {RatingSource.IMDB: None}


async def test_a_number_beats_a_null_from_another_source(sessions, item_id,
                                                        enrich):
    """Null — это «у него нет», а не значение: настоящее число из второго
    источника его не ждёт и не уступает ему места."""
    service = enrich(
        FakeRatings((RatingSource.IMDB,), found((RatingSource.IMDB, None))),
        FakeRatings((RatingSource.IMDB,), found((RatingSource.IMDB, 8.6))),
    )

    await service.enrich(item_id, Kind.MOVIE)

    assert await stored_ratings(sessions, item_id) == {RatingSource.IMDB: 8.6}


async def test_nothing_stale_costs_nothing_extra(sessions, engine, item_id,
                                                enrich):
    """Ради раннего выхода: карточек на странице пятьдесят, и лишний запрос на
    каждую — это пятьдесят запросов на одну прокрутку.

    Два запроса — это сроки годности и состояние оценок на показ. Третьим был бы
    поход за `imdb_id`, которого спрашивать уже незачем."""
    await ExternalRatingsRepository(sessions).record(
        item_id, ExternalRating(RatingSource.IMDB, 8.6, MOMENT)
    )
    client = FakeRatings((RatingSource.IMDB,), found((RatingSource.IMDB, 9.9)))
    counted = []

    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def count(conn, cursor, statement, *rest):
        counted.append(statement)

    try:
        await enrich(client).enrich(item_id, Kind.MOVIE)
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", count)

    assert client.asked == []
    assert len(counted) == 2, counted


async def test_a_rating_nobody_promised_is_not_written(sessions, item_id, enrich,
                                                      caplog):
    """На `PROVIDES` стоит и запись пустого значения, и подсчёт ожидаемого. Возьми
    оценку, которую клиент не объявлял, — и в карточке появится источник, которого
    показ не ждёт, а пустое значение по нему никто уже не напишет."""
    service = enrich(FakeRatings(
        (RatingSource.IMDB,),
        found((RatingSource.IMDB, 8.6), (RatingSource.KINOPOISK, 7.7)),
    ))

    with caplog.at_level("WARNING"):
        await service.enrich(item_id, Kind.MOVIE)

    assert await stored_ratings(sessions, item_id) == {RatingSource.IMDB: 8.6}
    assert "kinopoisk" in caplog.text


async def test_a_fresh_value_is_not_asked_about_again(sessions, item_id, enrich):
    await ExternalRatingsRepository(sessions).record(
        item_id, ExternalRating(RatingSource.IMDB, 8.6, MOMENT - timedelta(days=3))
    )
    client = FakeRatings((RatingSource.IMDB,), found((RatingSource.IMDB, 9.9)))

    await enrich(client).enrich(item_id, Kind.MOVIE)

    assert client.asked == []


async def test_a_stale_value_is_asked_about(sessions, item_id, enrich):
    await ExternalRatingsRepository(sessions).record(
        item_id, ExternalRating(RatingSource.IMDB, 8.6,
                                MOMENT - VALUE_TTL - timedelta(days=1))
    )
    client = FakeRatings((RatingSource.IMDB,), found((RatingSource.IMDB, 8.7)))

    await enrich(client).enrich(item_id, Kind.MOVIE)

    assert await stored_ratings(sessions, item_id) == {RatingSource.IMDB: 8.7}


async def test_an_empty_row_goes_stale_sooner(sessions, item_id, enrich):
    """У свежего релиза оценка ещё может появиться."""
    await ExternalRatingsRepository(sessions).record(
        item_id, ExternalRating(RatingSource.IMDB, None,
                                MOMENT - EMPTY_TTL - timedelta(days=1))
    )
    client = FakeRatings((RatingSource.IMDB,), found((RatingSource.IMDB, 8.6)))

    await enrich(client).enrich(item_id, Kind.MOVIE)

    assert client.asked == ["tt0816692"]


async def test_games_ask_nobody(sessions, enrich):
    """Оценки критиков у игр приходят даром — с самой карточкой.

    Само правило «у игр оценочных источников нет» живёт в реестре и проверено
    планом 2; здесь проверяется, что пустой список сервис переживает и в сеть не
    идёт."""
    item_id = await LibraryRepository(sessions).create(
        an_item("292030", "Ведьмак", kind=Kind.GAME, source=Source.STEAM)
    )
    client = FakeRatings((RatingSource.IMDB,), found((RatingSource.IMDB, 8.6)))

    await enrich(client).enrich(item_id, Kind.GAME)

    assert client.asked == []


async def test_without_an_imdb_id_nobody_is_asked(sessions, enrich):
    """`imdb_id` есть только в детальном ответе — без него спрашивать нечем."""
    item_id = await LibraryRepository(sessions).create(
        an_item("1", "Без идентификатора")
    )
    client = FakeRatings((RatingSource.IMDB,), found((RatingSource.IMDB, 8.6)))

    await enrich(client).enrich(item_id, Kind.MOVIE)

    assert client.asked == []


async def test_a_found_identifier_is_kept(sessions, item_id, enrich):
    """Кинопоиск заодно сообщает свой id — дальше по нему ходить дешевле."""
    answer = Found(Ratings(
        values=(ExternalRating(RatingSource.KINOPOISK, 8.6, MOMENT),),
        external_ids=(ExternalId(IdSource.KINOPOISK, "258687"),),
    ))
    service = enrich(FakeRatings((RatingSource.KINOPOISK,), answer))

    await service.enrich(item_id, Kind.MOVIE)

    stored = await ExternalIdsRepository(sessions).ids_of(item_id)
    assert (IdSource.KINOPOISK, "258687") in [(e.source, e.value) for e in stored]


async def test_an_identifier_taken_by_another_card_is_logged_not_raised(
    sessions, item_id, enrich, caplog
):
    other_id = await LibraryRepository(sessions).create(
        an_item("27205", "Начало")
    )
    await ExternalIdsRepository(sessions).put(
        other_id, ExternalId(IdSource.KINOPOISK, "258687")
    )
    answer = Found(Ratings(
        values=(ExternalRating(RatingSource.KINOPOISK, 8.6, MOMENT),),
        external_ids=(ExternalId(IdSource.KINOPOISK, "258687"),),
    ))
    service = enrich(FakeRatings((RatingSource.KINOPOISK,), answer))

    with caplog.at_level("WARNING"):
        await service.enrich(item_id, Kind.MOVIE)

    assert "258687" in caplog.text
    # Оценка при этом записана: занятый чужой идентификатор её не отменяет.
    assert await stored_ratings(sessions, item_id) == {RatingSource.KINOPOISK: 8.6}


async def test_the_first_value_wins_when_two_sources_know_the_same_rating(
    sessions, item_id, enrich
):
    """IMDb знают и MDBList, и OMDB. Побеждает тот, кого спросили первым, —
    иначе значение зависело бы от того, кто быстрее ответил по сети."""
    service = enrich(
        FakeRatings((RatingSource.IMDB,), found((RatingSource.IMDB, 8.6))),
        FakeRatings((RatingSource.IMDB,), found((RatingSource.IMDB, 7.1))),
    )

    await service.enrich(item_id, Kind.MOVIE)

    assert await stored_ratings(sessions, item_id) == {RatingSource.IMDB: 8.6}


async def test_a_value_arriving_beyond_the_request_is_kept(
    sessions, item_id, enrich
):
    """Оно уже приехало даром, а `fetched_at` от записи только свежее."""
    await ExternalRatingsRepository(sessions).record(
        item_id, ExternalRating(RatingSource.IMDB, 8.0, MOMENT - timedelta(days=1))
    )
    service = enrich(FakeRatings(
        (RatingSource.IMDB, RatingSource.METACRITIC),
        found((RatingSource.IMDB, 8.6), (RatingSource.METACRITIC, 74.0)),
    ))

    await service.enrich(item_id, Kind.MOVIE)

    rows = await ExternalRatingsRepository(sessions).ratings_of(item_id)
    fresh = {r.source: (r.value, r.fetched_at) for r in rows}
    assert fresh[RatingSource.IMDB] == (8.6, MOMENT)


async def test_a_client_with_nothing_stale_is_not_asked(sessions, item_id, enrich):
    """Лишний сетевой запрос на каждый показ карточки не заметил бы никто."""
    await ExternalRatingsRepository(sessions).record(
        item_id, ExternalRating(RatingSource.KINOPOISK, 8.6, MOMENT)
    )
    fresh = FakeRatings((RatingSource.KINOPOISK,),
                        found((RatingSource.KINOPOISK, 9.9)))
    stale = FakeRatings((RatingSource.IMDB,), found((RatingSource.IMDB, 8.6)))

    await enrich(fresh, stale).enrich(item_id, Kind.MOVIE)

    assert fresh.asked == []
    assert stale.asked == ["tt0816692"]


async def test_the_expected_set_is_what_the_clients_promise(sessions, enrich):
    """Показ вычитает приехавшее из ожидаемого, чтобы понять, где крутить
    кольцо. Ожидаемое знает только бэкенд."""
    service = enrich(
        FakeRatings((RatingSource.IMDB, RatingSource.ROTTEN), Missing()),
        FakeRatings((RatingSource.IMDB, RatingSource.KINOPOISK), Missing()),
    )

    assert service.expected(Kind.MOVIE) == [
        RatingSource.IMDB, RatingSource.ROTTEN, RatingSource.KINOPOISK
    ]
    assert service.expected(Kind.GAME) == []


async def test_a_broken_client_names_itself_in_the_log(enrich, item_id, caplog):
    """Сорвавшийся клиент отказ наружу не отдаёт — обогащение просто вернёт то,
    что лежит в базе, — и единственный след остаётся в логе. Значит имя в нём и
    есть весь ответ на вопрос «кто не ответил».

    Взятое из `PROVIDES` имя врёт: первым там и у MDBList, и у OMDB стоит `imdb`,
    так что оба сорвавшихся источника выглядели бы одним."""
    service = enrich(Breaking((RatingSource.IMDB, RatingSource.ROTTEN), None,
                              name="omdb"))

    with caplog.at_level("ERROR"):
        await service.enrich(item_id, Kind.MOVIE)

    assert any(message.startswith("omdb:") for message in ours(caplog))
    assert not any(message.startswith("imdb:") for message in ours(caplog))
