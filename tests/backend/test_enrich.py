"""Третий круг: оценки агрегаторов и сроки их годности."""

from datetime import timedelta

from sqlalchemy import event

from backend.model import (
    ExternalRating,
    Kind,
    Missing,
    RatingSource,
    Reason,
    Refusal,
    Source,
)
from backend.storage.repository.external import (
    EMPTY_TTL,
    VALUE_TTL,
    ExternalRatingsRepository,
)
from backend.storage.repository.library import LibraryRepository
from tests.backend.enriching import (
    Breaking,
    FakeRatings,
    found,
    stored_ratings,
)
from tests.conftest import MOMENT, an_item, ours


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
    assert [r.levelname for r in caplog.records
            if r.name.startswith("backend")] == ["ERROR"]
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

    assert client.asked == [("tt0816692", Kind.MOVIE)]


async def test_an_honest_zero_reaches_the_row(sessions, item_id, enrich):
    """Ноль — это оценка, просто самая низкая, и от «у источника её нет» он
    отличается только проверкой на `None`. Проверка на ложность их сливает, и
    ноль записался бы пустым значением — то есть «нет оценки» на месяц.

    Сторож стоял слоем ниже, у разбора ответа; сюда, к проводке через сервис,
    ноль не доезжал ни в одном тесте."""
    client = FakeRatings((RatingSource.IMDB,), found((RatingSource.IMDB, 0.0)))

    await enrich(client).enrich(item_id, Kind.MOVIE)

    assert await stored_ratings(sessions, item_id) == {RatingSource.IMDB: 0.0}


async def test_a_series_is_asked_about_as_a_series(sessions, item_id, enrich):
    """Один тип содержимого проверить мало: подставь клиенту `Kind.MOVIE`
    жёстко, и фильмовый тест этого не заметит. У MDBList из типа собирается
    адрес — `show` против `movie`, — и жёсткая подстановка оставила бы все
    сериалы без оценок: источник ответил бы «такого нет», а это пустая строка
    на месяц."""
    client = FakeRatings((RatingSource.IMDB,), found((RatingSource.IMDB, 9.1)))

    await enrich(client).enrich(item_id, Kind.SERIES)

    assert client.asked == [("tt0816692", Kind.SERIES)]


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
    assert stale.asked == [("tt0816692", Kind.MOVIE)]


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
