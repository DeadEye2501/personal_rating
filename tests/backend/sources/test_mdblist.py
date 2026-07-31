"""MDBList: квота, битый ключ и чужой периметр — три разные беды."""

from datetime import timedelta

import httpx

from backend.model import Found, Kind, Missing, RatingSource, Reason, Refusal
from backend.sources.http import SourceHttp
from backend.sources.ratings.mdblist.client import MdbListClient
from backend.sources.ratings.mdblist.parse import parse_ratings
from tests.conftest import responding


async def ask(transport, kind=Kind.MOVIE):
    client = MdbListClient(SourceHttp("mdblist", transport=transport), api_key="k")
    result = await client.ratings("tt0816692", kind)
    await client.aclose()
    return result


def test_ratings_are_split_by_owner(fixture):
    """Имя источника — владелец оценки. Метакритика зрителей и Trakt мы не
    заводим: строка в базе должна значить одно и то же всегда."""
    answer = parse_ratings(fixture("mdblist/found.json"))

    owners = {one.source for one in answer.values}
    assert owners, "ни одной оценки не разобрано"
    assert owners == {
        RatingSource.IMDB,
        RatingSource.TMDB,
        RatingSource.ROTTEN,
        RatingSource.METACRITIC,
    }


def test_each_owner_keeps_its_own_scale(fixture):
    """IMDb десятибалльный, Rotten и Metacritic стобалльные. Приводить их к
    одной шкале нельзя: спека велит хранить как отдал источник."""
    by_owner = {one.source: one.value for one in parse_ratings(
        fixture("mdblist/found.json")
    ).values}

    assert by_owner[RatingSource.IMDB] == 8.7
    assert by_owner[RatingSource.METACRITIC] == 74
    assert by_owner[RatingSource.ROTTEN] == 73


def test_null_score_is_reported_as_an_empty_value():
    """У найденного объекта конкретный рейтинг бывает null. Это ответ «у нас
    такой оценки нет» — он пишется пустым значением, а не выбрасывается."""
    payload = {"ratings": [{"source": "imdb", "value": None},
                           {"source": "metacritic", "value": 74}]}

    by_owner = {one.source: one.value for one in parse_ratings(payload).values}

    assert by_owner == {RatingSource.IMDB: None, RatingSource.METACRITIC: 74.0}


def test_an_honest_zero_is_not_an_empty_value():
    """Пустое значение означает «у источника такой оценки нет», и ноль от него
    надо отличать: это оценка, просто самая низкая. Проверка на ложность их
    сливает, проверка на `None` — нет."""
    payload = {"ratings": [{"source": "imdb", "value": 0}]}

    assert [one.value for one in parse_ratings(payload).values] == [0.0]


def test_unknown_owner_is_ignored():
    payload = {"ratings": [{"source": "letterboxd", "value": 4.2}]}

    assert parse_ratings(payload).values == ()


async def test_modern_endpoint_is_used():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"ratings": []})

    await ask(httpx.MockTransport(handler))

    # Адрес пишется буквой, а не через ту же константу, что и в коде: сверка с
    # объявлением переезжает вместе с ним и не проверяет ничего.
    assert "https://api.mdblist.com/imdb/movie/" in seen["url"]
    # Легаси mdblist.com/api сливает битый ключ и лимит в один 503.
    assert "mdblist.com/api" not in seen["url"]
    assert "apikey=k" in seen["url"]


async def test_series_go_to_the_show_path():
    """Адрес — /{provider}/{type}/{id}: у сериала type другой."""
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"ratings": []})

    await ask(httpx.MockTransport(handler), kind=Kind.SERIES)

    assert "/imdb/show/" in seen["url"]


async def test_movies_go_to_the_movie_path():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"ratings": []})

    await ask(httpx.MockTransport(handler))

    assert "/imdb/movie/tt0816692" in seen["url"]


async def test_recorded_quota_is_a_refusal_with_the_named_delay(replay, meta):
    """Срок берётся из заголовка, а не из своего запасного: источник называет
    его сам, и своё значение здесь было бы догадкой поверх факта."""
    info = meta("mdblist/quota.json")
    assert info["status"] == 429

    result = await ask(replay("mdblist/quota.json"))

    assert isinstance(result, Refusal)
    assert (result.source, result.reason) == ("mdblist", Reason.QUOTA)
    assert result.retry_after == timedelta(seconds=int(info["headers"]["retry-after"]))


async def test_quota_without_a_named_delay_falls_back_to_an_hour():
    result = await ask(responding(429, json={"error": "Daily API limit exceeded!"}))

    assert isinstance(result, Refusal)
    assert (result.source, result.reason) == ("mdblist", Reason.QUOTA)
    assert result.retry_after == timedelta(hours=1)


async def test_a_delay_that_is_not_a_number_falls_back_too():
    """`Retry-After` разрешено присылать датой, а не секундами. `int` на ней
    падает, и отказ по квоте превратился бы в исключение из клиента."""
    result = await ask(
        responding(429, json={"error": "Daily API limit exceeded!"},
                   headers={"Retry-After": "Wed, 29 Jul 2026 21:00:00 GMT"})
    )

    assert isinstance(result, Refusal)
    assert result.retry_after == timedelta(hours=1)


async def test_quota_trips_the_breaker():
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(429, json={"error": "Daily API limit exceeded!"},
                              headers={"Retry-After": "600"})

    client = MdbListClient(
        SourceHttp("mdblist", transport=httpx.MockTransport(handler)), api_key="k"
    )
    await client.ratings("tt0816692", Kind.MOVIE)
    second = await client.ratings("tt0111161", Kind.MOVIE)
    await client.aclose()

    assert isinstance(second, Refusal)
    assert calls == 1, "второй запрос ушёл в сеть после исчерпанной квоты"


async def test_recorded_bad_key_is_a_refusal(replay, meta):
    """Имя источника проверяется вместе с причиной: клиенты MDBList и OMDB
    написаны по одному шаблону и стоят рядом, имя в обоих — литерал, и подмена
    одного на другой отправила бы человека править не тот ключ."""
    assert meta("mdblist/bad_key.json")["status"] == 401

    result = await ask(replay("mdblist/bad_key.json"))

    assert isinstance(result, Refusal)
    assert (result.source, result.reason) == ("mdblist", Reason.KEY)


async def test_a_request_without_a_key_is_the_same_refusal(replay, meta):
    """Ключа нет — обычный отказ источника, а не особый случай первого
    запуска. Приезжает он тем же кодом, что и битый ключ."""
    assert meta("mdblist/no_key.json")["status"] == 401

    result = await ask(replay("mdblist/no_key.json"))

    assert isinstance(result, Refusal)
    assert (result.source, result.reason) == ("mdblist", Reason.KEY)


async def test_cloudflare_wall_is_not_a_key_problem(replay, meta):
    """«error code: 1010» означает, что запрос до MDBList не дошёл. Считать
    это битым ключом — значит искать неисправность не там, где она есть."""
    assert meta("mdblist/cloudflare_403.txt")["status"] == 403

    result = await ask(replay("mdblist/cloudflare_403.txt"))

    assert isinstance(result, Refusal)
    assert (result.source, result.reason) == ("mdblist", Reason.NETWORK)


async def test_missing_object_is_an_answer():
    result = await ask(responding(404, json={"error": "Item not found"}))

    assert isinstance(result, Missing)


async def test_a_404_without_json_is_not_an_absence(fixture):
    """Отрицательный факт — только по разобранному телу. Перед MDBList стоит
    Cloudflare, и его страница приезжает под чужим кодом обычным текстом. Тело
    берём записанное — то самое, что приехало под 403; своего 404 от периметра у
    нас не записано, а сочинять тело там, где форма и есть предмет проверки,
    значит проверять собственную выдумку.

    Записать такую страницу как ответ значит объявить на неделю, что у фильма
    нет оценок ни в IMDb, ни в TMDB, ни в Rotten, ни в Metacritic — сразу четыре
    пустые строки по странице, которая до MDBList даже не дошла.

    Причина `BROKEN`, а не `NETWORK`: чей это 404 — периметра или самого
    MDBList, — по телу не видно, и живьём такой ответ у него не наблюдали вовсе.
    Имя источника сверяется вместе с причиной по тому же доводу, что записан у
    соседей: в клиенте оно литерал, а MDBList и OMDB написаны по одному
    образцу."""
    result = await ask(responding(404, text=fixture("mdblist/cloudflare_403.txt")))

    assert isinstance(result, Refusal)
    assert (result.source, result.reason) == ("mdblist", Reason.BROKEN)


async def test_cache_building_is_a_retry_not_an_absence():
    """202 и Retry-After: 5 — «кеш строится, повтори». В базу не пишем ничего:
    это не отсутствие оценки, а её отложенность."""
    result = await ask(responding(202, json={}, headers={"Retry-After": "5"}))

    assert isinstance(result, Refusal)
    assert (result.source, result.reason) == ("mdblist", Reason.RATE)
    assert result.retry_after == timedelta(seconds=5)


async def test_server_error_is_a_refusal():
    result = await ask(responding(500, json={"error": "An error occurred"}))

    assert isinstance(result, Refusal)
    assert (result.source, result.reason) == ("mdblist", Reason.BROKEN)


async def test_unexpected_shape_does_not_crash():
    result = await ask(responding(200, json={"ratings": "не список"}))

    assert isinstance(result, Refusal)
    assert (result.source, result.reason) == ("mdblist", Reason.BROKEN)


async def test_recorded_found_ratings_come_back(replay):
    result = await ask(replay("mdblist/found.json"))

    assert isinstance(result, Found)
    assert result.value.values
