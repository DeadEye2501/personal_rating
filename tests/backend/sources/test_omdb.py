"""OMDB: единственный источник, у которого отказ приходит под кодом 401, а
отсутствие — под 200."""

from datetime import datetime, timedelta

import httpx

from backend.model import Found, Kind, Missing, RatingSource, Reason, Refusal
from backend.sources.backoff import until_midnight
from backend.sources.http import SourceHttp
from backend.sources.ratings.omdb.client import OmdbClient
from backend.sources.ratings.omdb.parse import parse_ratings
from tests.conftest import FakeClock, counting, responding


async def ask(transport):
    client = OmdbClient(SourceHttp("omdb", transport=transport), api_key="k")
    result = await client.ratings("tt0816692", Kind.MOVIE)
    await client.aclose()
    return result


def test_imdb_rating_is_taken_from_its_own_field(fixture):
    answer = parse_ratings(fixture("omdb/found.json"))

    imdb = [one for one in answer.values if one.source is RatingSource.IMDB]
    assert [one.value for one in imdb] == [8.7]


def test_the_list_wins_over_the_separate_field():
    """В записанном ответе оба числа совпадают, и на нём потеря списка
    незаметна: IMDb дописался бы из отдельного поля и выглядел бы разобранным.
    Отсюда выдуманное тело, где числа разные."""
    payload = {
        "imdbRating": "1.0",
        "Ratings": [{"Source": "Internet Movie Database", "Value": "8.6/10"}],
    }

    values = parse_ratings(payload).values

    assert [(one.source, one.value) for one in values] == [(RatingSource.IMDB, 8.6)]


def test_every_owner_omdb_knows_is_taken(fixture):
    answer = parse_ratings(fixture("omdb/found.json"))

    assert {one.source for one in answer.values} == {
        RatingSource.IMDB,
        RatingSource.ROTTEN,
        RatingSource.METACRITIC,
    }


def test_rotten_tomatoes_keeps_its_own_scale():
    """Значение лежит в том виде, в каком его отдал источник: Rotten
    стобалльный, IMDb десятибалльный. Шкала выводится из имени при показе."""
    payload = {"Ratings": [{"Source": "Rotten Tomatoes", "Value": "72%"}]}

    values = parse_ratings(payload).values

    assert [(one.source, one.value) for one in values] == [(RatingSource.ROTTEN, 72.0)]


def test_fraction_form_is_understood():
    payload = {"Ratings": [{"Source": "Metacritic", "Value": "74/100"}]}

    assert parse_ratings(payload).values[0].value == 74.0


def test_the_ten_point_form_keeps_the_fraction_part():
    """«8.6/10» — обрезав по точке, получили бы восьмёрку вместо 8.6."""
    payload = {"Ratings": [{"Source": "Internet Movie Database", "Value": "8.6/10"}]}

    assert parse_ratings(payload).values[0].value == 8.6


def test_an_owner_we_do_not_keep_is_ignored():
    """Строка в базе должна значить одно и то же всегда: чужого владельца туда
    не заводим, а подставить его вместо известного — значит записать оценку
    Letterboxd как оценку IMDb."""
    payload = {"Ratings": [{"Source": "Letterboxd", "Value": "4.2"}]}

    assert parse_ratings(payload).values == ()


def test_na_is_not_a_rating():
    payload = {"imdbRating": "N/A", "Ratings": []}

    assert parse_ratings(payload).values == ()


def test_the_separate_imdb_field_does_not_duplicate_the_list():
    """IMDb приезжает дважды — списком и отдельным полем. Взяв оба, мы бы
    записали одному владельцу две строки, а в базе на них один ключ."""
    payload = {
        "imdbRating": "8.6",
        "Ratings": [{"Source": "Internet Movie Database", "Value": "8.6/10"}],
    }

    assert len(parse_ratings(payload).values) == 1


def test_the_separate_imdb_field_is_used_when_the_list_has_none():
    payload = {"imdbRating": "8.6", "Ratings": []}

    values = parse_ratings(payload).values

    assert [(one.source, one.value) for one in values] == [(RatingSource.IMDB, 8.6)]


def test_until_midnight_counts_to_the_next_day():
    assert until_midnight(datetime(2026, 7, 27, 23, 0)) == timedelta(hours=1)
    assert until_midnight(datetime(2026, 7, 27, 0, 30)) == timedelta(
        hours=23, minutes=30
    )


async def test_recorded_missing_object_arrives_under_two_hundred(replay, meta):
    """Единственное исключение среди источников: отказ пришёл бы с 401, а это
    ответ — «такого у нас нет»."""
    assert meta("omdb/not_found.json")["status"] == 200

    assert isinstance(await ask(replay("omdb/not_found.json")), Missing)


async def test_all_three_texts_under_two_hundred_mean_the_same():
    for text in ("Movie not found!", "Error getting data.", "Incorrect IMDb ID."):
        result = await ask(responding(200, json={"Response": "False", "Error": text}))

        assert isinstance(result, Missing), text


async def test_a_recorded_broken_identifier_is_an_answer_too(replay, meta):
    """«Incorrect IMDb ID.» приезжает под тем же кодом 200: для нас это то же
    «такого у нас нет», а не отказ."""
    assert meta("omdb/bad_id.json")["status"] == 200

    assert isinstance(await ask(replay("omdb/bad_id.json")), Missing)


async def test_an_unexpected_status_is_a_refusal():
    """Кроме 200 и 401 у OMDB кодов не видели, но сервер вправе прислать
    любой: без этой ветки ответ ушёл бы в разбор и стал бы `Found` с пустотой
    или исключением."""
    result = await ask(responding(503, json={"Response": "False"}))

    assert isinstance(result, Refusal)
    assert (result.source, result.reason) == ("omdb", Reason.BROKEN)
    assert "503" in result.detail


async def test_recorded_quota_is_told_apart_from_a_bad_key(replay, meta):
    """Под одним кодом 401 живут две разные беды, и различает их только текст.

    Имя источника проверяется вместе с причиной: клиенты MDBList и OMDB написаны
    по одному шаблону и стоят рядом, имя в обоих — литерал, и подмена одного на
    другой отправила бы человека править не тот ключ."""
    assert meta("omdb/quota.json")["status"] == 401
    assert meta("omdb/bad_key.json")["status"] == 401

    quota = await ask(replay("omdb/quota.json"))
    assert isinstance(quota, Refusal)
    assert (quota.source, quota.reason) == ("omdb", Reason.QUOTA)

    key = await ask(replay("omdb/bad_key.json"))
    assert isinstance(key, Refusal)
    assert (key.source, key.reason) == ("omdb", Reason.KEY)


async def test_a_request_without_a_key_is_a_key_refusal(replay):
    result = await ask(replay("omdb/no_key.json"))

    assert isinstance(result, Refusal)
    assert (result.source, result.reason) == ("omdb", Reason.KEY)


async def test_substring_match_is_loose():
    """Точный текст взят из issue-трекера, а не из документации: полного
    списка значений `Error` не существует."""
    result = await ask(responding(401, json={"Error": "Daily request limit exceeded"}))

    assert (result.source, result.reason) == ("omdb", Reason.QUOTA)


async def test_the_text_is_matched_regardless_of_case():
    """Формулировки известны из issue-трекера, а не из документации, и регистр
    в них не обещан никем: «Limit» с большой буквы уехало бы в поломку."""
    result = await ask(responding(401, json={"Error": "Request LIMIT reached!"}))

    assert (result.source, result.reason) == ("omdb", Reason.QUOTA)


async def test_unknown_four_oh_one_is_treated_as_temporary():
    """Ошибаемся в сторону «повторим позже», а не «ключ битый навсегда»."""
    result = await ask(responding(401, json={"Error": "нечто новое"}))

    assert isinstance(result, Refusal)
    assert (result.source, result.reason) == ("omdb", Reason.BROKEN)


async def test_quota_waits_until_the_next_day():
    """Квота суточная, заголовков OMDB не отдаёт. Пробовать раньше
    бессмысленно: придёт тот же отказ, а потраченный запрос не вернуть."""
    clock = FakeClock()
    clock.now = datetime(2026, 7, 27, 21, 0)
    http = SourceHttp(
        "omdb",
        clock=clock,
        transport=responding(401, json={"Error": "Request limit reached!"}),
    )
    client = OmdbClient(http, api_key="k")

    result = await client.ratings("tt0816692", Kind.MOVIE)
    await client.aclose()

    assert result.retry_after == timedelta(hours=3)


async def test_quota_trips_the_breaker():
    transport, seen = counting(responding(401, json={"Error": "Request limit reached!"}))

    client = OmdbClient(
        SourceHttp("omdb", transport=transport), api_key="k"
    )
    await client.ratings("tt0816692", Kind.MOVIE)
    second = await client.ratings("tt0111161", Kind.MOVIE)
    await client.aclose()

    assert isinstance(second, Refusal)
    assert len(seen) == 1, "второй запрос ушёл в сеть после исчерпанной квоты"


async def test_a_bad_key_does_not_trip_the_breaker():
    """Битый ключ сроком не лечится: закрыв источник на сутки, мы не дали бы
    человеку и шанса вписать новый."""
    transport, seen = counting(responding(401, json={"Error": "Invalid API key!"}))

    client = OmdbClient(
        SourceHttp("omdb", transport=transport), api_key="k"
    )
    await client.ratings("tt0816692", Kind.MOVIE)
    await client.ratings("tt0111161", Kind.MOVIE)
    await client.aclose()

    assert len(seen) == 2


async def test_the_key_and_the_identifier_are_sent():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"Response": "True", "Ratings": []})

    await ask(httpx.MockTransport(handler))

    assert "apikey=k" in seen["url"]
    assert "i=tt0816692" in seen["url"]


async def test_unexpected_shape_does_not_crash():
    result = await ask(responding(200, json={"Response": "True", "Ratings": "не список"}))

    assert isinstance(result, Refusal)


async def test_a_json_array_does_not_crash():
    """Тело разобралось — ещё не значит объект. У массива нет `.get`, и без
    проверки `AttributeError` улетает из клиента наружу."""
    result = await ask(responding(200, json=[1, 2]))

    assert isinstance(result, Refusal)
    assert (result.source, result.reason) == ("omdb", Reason.BROKEN)


async def test_a_body_that_is_not_json_does_not_crash():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, text="<html>nope</html>")
    )

    result = await ask(transport)

    assert isinstance(result, Refusal)
    assert (result.source, result.reason) == ("omdb", Reason.BROKEN)


async def test_recorded_found_ratings_come_back(replay):
    result = await ask(replay("omdb/found.json"))

    assert isinstance(result, Found)
    assert result.value.values
