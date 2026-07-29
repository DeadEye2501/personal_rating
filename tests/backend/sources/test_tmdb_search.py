"""Первый круг загрузки: кандидат выдачи — ещё не карточка."""

import httpx

from backend.model import GenreSource, Kind, Source
from backend.sources.errors import Found, Reason, Refusal
from backend.sources.http import SourceHttp
from backend.sources.tmdb.client import TmdbClient
from backend.sources.tmdb.parse import parse_search


def test_search_gives_candidates_not_cards(fixture):
    payload = fixture("tmdb/search_movie.json")

    hits = parse_search(payload, Kind.MOVIE)

    assert len(hits) == len(payload["results"]), "часть выдачи потерялась"
    first = hits[0]
    assert first.source is Source.TMDB
    assert first.kind is Kind.MOVIE
    assert first.title
    assert first.synopsis
    # Строкой, а не числом: идентификатор источника едет в базу текстовой
    # колонкой, и `157336` разошлось бы с `"157336"` молча — карточка нашлась бы
    # заведённой заново вместо найденной.
    assert isinstance(first.source_id, str) and first.source_id.isdigit()


def test_the_original_title_is_not_the_translated_one(fixture):
    """Оба поля приходят в одном ответе, и подстановка одного вместо другого
    видна только тем, что они разные: «Интерстеллар» против «Interstellar»."""
    first = parse_search(fixture("tmdb/search_movie.json"), Kind.MOVIE)[0]

    assert first.original_title
    assert first.original_title != first.title


def test_genres_arrive_as_identifiers_without_names(fixture):
    """Имён жанров в выдаче нет: их даёт наш справочник по genre_ids."""
    hits = parse_search(fixture("tmdb/search_movie.json"), Kind.MOVIE)

    assert hits[0].genre_ext_ids, "жанры не разобраны"
    assert all(
        space is GenreSource.TMDB and ext_id.isdigit()
        for space, ext_id in hits[0].genre_ext_ids
    )


def test_tmdb_rating_comes_free_with_the_search(fixture):
    """vote_average приезжает в том же ответе — за него не платим запросом."""
    hits = parse_search(fixture("tmdb/search_movie.json"), Kind.MOVIE)

    rated = [hit for hit in hits if hit.source_rating is not None]
    assert rated, "ни у одного кандидата нет оценки TMDB"
    assert 0 < rated[0].source_rating <= 10


def test_series_are_parsed_from_their_own_fields(fixture):
    """У сериала название лежит в name и original_name, а не в title."""
    hits = parse_search(fixture("tmdb/search_tv.json"), Kind.SERIES)

    assert hits[0].kind is Kind.SERIES
    assert hits[0].title
    assert hits[0].original_title


def test_a_movie_read_by_the_series_rules_loses_its_title():
    """Ключи полей разведены по типу содержимого, и подстановка не косметика:
    прочитанный как сериал фильм приезжает безымянным."""
    movie = {"results": [{"id": 1, "title": "Интерстеллар", "release_date": "2014"}]}

    assert parse_search(movie, Kind.SERIES)[0].title == ""


def test_the_year_comes_from_the_date_of_the_right_type():
    """У сериала дата в first_air_date, у фильма — в release_date."""
    series = {"results": [{"id": 1, "name": "Andor", "first_air_date": "2022-09-21"}]}

    assert parse_search(series, Kind.SERIES)[0].year == 2022


def test_a_date_that_is_not_a_date_leaves_the_year_empty():
    """TMDB отдаёт `release_date: ""` у необъявленного к выходу. `int("")`
    уронил бы разбор всей выдачи из-за одной строки в ней."""
    payload = {"results": [{"id": 1, "title": "Без даты", "release_date": ""}]}

    assert parse_search(payload, Kind.MOVIE)[0].year is None


def test_empty_result_is_an_empty_list_not_a_failure():
    assert parse_search({"results": []}, Kind.MOVIE) == []


def test_poster_path_becomes_a_full_url(fixture):
    hits = parse_search(fixture("tmdb/search_movie.json"), Kind.MOVIE)

    with_poster = [hit for hit in hits if hit.poster_url]
    assert with_poster
    assert with_poster[0].poster_url.startswith("https://")
    assert "w500" in with_poster[0].poster_url


def test_a_candidate_without_a_poster_gets_no_url():
    """`poster_path` приходит `null`, и склеенный с базой он дал бы ссылку на
    несуществующую картинку — отличить её от настоящей было бы нечем."""
    payload = {"results": [{"id": 1, "title": "Без постера", "poster_path": None}]}

    assert parse_search(payload, Kind.MOVIE)[0].poster_url == ""


async def test_client_asks_the_right_endpoint_and_language(fixture):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json=fixture("tmdb/search_movie.json"))

    client = TmdbClient(
        SourceHttp("tmdb", transport=httpx.MockTransport(handler)), api_key="k"
    )
    result = await client.search("Интерстеллар", Kind.MOVIE)
    await client.aclose()

    assert isinstance(result, Found)
    assert result.value
    assert "/search/movie" in seen["url"]
    assert "language=ru-RU" in seen["url"]
    assert "query=" in seen["url"]
    # Без ключа TMDB отвечает 401, и разбор увидит не выдачу, а объяснение
    # отказа — то есть отсутствие ключа приедет к человеку как «ничего не
    # нашлось».
    assert "api_key=k" in seen["url"]


async def test_series_search_goes_to_the_tv_endpoint(fixture):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json=fixture("tmdb/search_tv.json"))

    client = TmdbClient(
        SourceHttp("tmdb", transport=httpx.MockTransport(handler)), api_key="k"
    )
    await client.search("Andor", Kind.SERIES)
    await client.aclose()

    assert "/search/tv" in seen["url"]


async def test_a_body_that_is_not_a_search_result_becomes_a_refusal():
    """Разбор чужого JSON падает не только `ValueError`, и наружу из клиента не
    должно вылетать ничего: иначе поиск роняет запрос вместо того, чтобы
    вернуть отказ."""
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"results": [{"нет": "ключа id"}]})
    )
    client = TmdbClient(SourceHttp("tmdb", transport=transport), api_key="k")

    result = await client.search("что угодно", Kind.MOVIE)
    await client.aclose()

    assert isinstance(result, Refusal)
    assert result.reason is Reason.BROKEN
    assert result.source == "tmdb"


async def test_a_refusal_from_the_wire_passes_through_untouched():
    """Сеть отказала — исход уже готов. Причина обязана дожить до вызывающего:
    разобранный как тело, отказ сети приезжает к нему как «источник сломался»,
    и человек читает про поломку TMDB вместо пропавшего интернета."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("нет сети", request=request)

    client = TmdbClient(
        SourceHttp("tmdb", transport=httpx.MockTransport(handler)), api_key="k"
    )
    result = await client.search("Интерстеллар", Kind.MOVIE)
    await client.aclose()

    assert isinstance(result, Refusal)
    assert result.reason is Reason.NETWORK
