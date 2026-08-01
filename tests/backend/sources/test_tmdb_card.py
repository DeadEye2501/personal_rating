"""Второй круг загрузки: карточка, которую уже можно записать."""

from datetime import date

import httpx
import pytest

from backend.model import (
    Found,
    GenreSource,
    Kind,
    PersonRole,
    RatingSource,
    Reason,
    Refusal,
    SeriesCounts,
    Source,
)
from backend.sources.http import SourceHttp
from backend.sources.tmdb.client import TmdbClient
from backend.sources.tmdb.parse import (
    Incomplete,
    parse_movie,
    parse_series,
    parse_series_counts,
)


def test_movie_card_carries_what_the_search_could_not(fixture):
    card = parse_movie(fixture("tmdb/movie_detail.json"))

    assert card.item.source is Source.TMDB
    assert card.item.kind is Kind.MOVIE
    assert card.item.runtime and card.item.runtime > 0
    assert card.item.title
    assert card.item.original_title != card.item.title
    assert card.item.synopsis
    assert card.item.poster_url.startswith("https://")
    assert "w500" in card.item.poster_url
    assert card.genre_ext_ids
    # Строки в базе ещё нет — тот же уговор, что у ручной карточки.
    assert card.item.id == 0


def test_the_full_release_date_survives_not_only_the_year(fixture):
    """Год нужен ленте, полная дата — карточке; и раз источник отдал обе,
    терять вторую значило бы идти за ней вторым запросом."""
    card = parse_movie(fixture("tmdb/movie_detail.json"))

    assert card.item.released_at == date(2014, 11, 5)
    assert card.item.year == 2014


def test_genres_come_from_the_named_block_not_the_search_one(fixture):
    """В детальном ответе жанры — объекты с именами, а не голые числа, и
    идентификатор лежит внутри объекта."""
    card = parse_movie(fixture("tmdb/movie_detail.json"))

    assert [ext_id for _space, ext_id in card.genre_ext_ids] == ["12", "18", "878"]
    # Пространство едет вместе с номером: `18` — это драма у TMDB и что угодно
    # другое у Steam, а справочник переводит номер по пространству.
    assert {space for space, _ in card.genre_ext_ids} == {GenreSource.TMDB}


def test_the_tmdb_rating_is_stored_on_the_hundred_scale():
    """Шкала TMDB стобалльная — решено пользователем 02.08.2026. Собственное
    `vote_average` приезжает десятибалльным, а MDBList отдаёт ту же оценку
    сотней: не приведи одно к другому, и в ленте рядом встанут «TMDB 8.4» и
    «TMDB 84», означающие одно и то же."""
    payload = {"id": 1, "title": "Одиссея", "vote_average": 8.4,
               "credits": {"cast": [], "crew": []}}

    assert parse_movie(payload).ratings[0].value == 84


def test_a_film_nobody_rated_has_no_rating():
    """У неоценённого `vote_average` приходит нулём, и записать его значило бы
    объявить, что фильм оценили в ноль."""
    payload = {"id": 1, "title": "Никем не смотрено", "vote_average": 0,
               "credits": {"cast": [], "crew": []}}

    assert parse_movie(payload).ratings == ()


def test_movie_imdb_id_is_taken_from_the_top_level(fixture):
    """Довесок external_ids фильму не нужен — id лежит прямо в ответе."""
    card = parse_movie(fixture("tmdb/movie_detail.json"))

    imdb = [one for one in card.external_ids if one.source == "imdb"]
    assert imdb and imdb[0].value.startswith("tt")


def test_an_empty_imdb_id_is_not_an_identifier(fixture):
    """TMDB кладёт в `imdb_id` пустую строку, когда его не знает. Записать её
    значит завести в базе идентификатор, по которому не спросить ни MDBList, ни
    OMDB, ни Кинопоиск, — а строка займёт пару уникальности."""
    payload = fixture("tmdb/movie_detail.json") | {"imdb_id": ""}

    card = parse_movie(payload)

    assert card.external_ids == ()


def test_tmdb_own_rating_survives_into_the_card(fixture):
    """В SearchHit она попадала, а после сохранения карточки исчезала бы до
    приезда MDBList — при том что приходит в этом же ответе даром."""
    card = parse_movie(fixture("tmdb/movie_detail.json"))

    own = [one for one in card.ratings if one.source is RatingSource.TMDB]
    assert own and 10 < own[0].value <= 100


def test_every_person_carries_the_tmdb_identity(fixture):
    """Без идентификатора два разных актёра-тёзки склеились бы в одну строку
    молча — человек в этом даже не участвует."""
    card = parse_movie(fixture("tmdb/movie_detail.json"))

    assert card.people
    for credit in card.people:
        assert credit.source is Source.TMDB, credit.name
        assert credit.source_id and credit.source_id.isdigit(), credit.name


def test_two_namesakes_from_tmdb_stay_apart(fixture):
    payload = dict(fixture("tmdb/movie_detail.json"))
    payload["credits"] = {
        "cast": [{"id": 1, "name": "Василий Пупкин", "order": 0},
                 {"id": 2, "name": "Василий Пупкин", "order": 1}],
        "crew": [],
    }

    identities = {credit.source_id for credit in parse_movie(payload).people}

    assert identities == {"1", "2"}


def test_director_is_pulled_from_the_crew(fixture):
    """Именно режиссёр, а не «кто-то из титров»: в них 512 человек, и отбор по
    роли легко перевернуть — тогда режиссёром станет каждый, кроме него."""
    card = parse_movie(fixture("tmdb/movie_detail.json"))

    directors = [one for one in card.people if one.role is PersonRole.DIRECTOR]
    assert [one.name for one in directors] == ["Кристофер Нолан"]


def test_the_rest_of_the_crew_stays_out(fixture):
    """В титрах «Интерстеллара» полторы сотни человек, и роли для них у нас
    нет: взяв всех, карточка получила бы гримёров вперемешку с актёрами."""
    card = parse_movie(fixture("tmdb/movie_detail.json"))

    roles = {credit.role for credit in card.people}
    assert roles == {PersonRole.ACTOR, PersonRole.DIRECTOR}


def test_actors_are_placed_by_the_billing_of_the_source(fixture):
    """Без порядка главные роли не отличить от эпизодических, и порядок этот —
    `order` из ответа, а не номер строки.

    Проверяется на сериале, хотя разбор состава общий: в записанном ответе фильма
    `order` совпадает с номером строки, и подмена одного другим прошла бы там
    молча — как и «позиция всегда ноль»."""
    card = parse_series(fixture("tmdb/tv_detail.json"))

    actors = [one for one in card.people if one.role is PersonRole.ACTOR]
    positions = [one.position for one in actors]
    assert min(positions) == 0
    assert positions != list(range(len(positions)))
    assert len(set(positions)) > 5


def test_an_actor_without_a_place_in_the_credits_falls_back_to_arrival(fixture):
    """`order` есть у каждого актёра в обоих записанных ответах, поэтому умолчание
    у `row.get` не исполнялось ни на одном теле: и `row["order"]`, и
    `row.get("order", 0)` проходили молча.

    Умолчание держим: ключа может не оказаться, а разбор без него отказал бы всей
    карточкой. Номер строки — единственный порядок, который тогда известен."""
    payload = fixture("tmdb/tv_detail.json")
    for row in payload["aggregate_credits"]["cast"]:
        row.pop("order", None)

    actors = [one for one in parse_series(payload).people
              if one.role is PersonRole.ACTOR]

    assert [one.position for one in actors] == list(range(len(actors)))


def test_series_card_has_seasons_and_episodes(fixture):
    """В карточке показывается «2 сезона, 24 серии» — оба числа отсюда."""
    card = parse_series(fixture("tmdb/tv_detail.json"))

    assert card.item.source_id == "83867"
    assert card.item.seasons_count == 2
    assert card.item.episodes_count == 24
    assert card.item.synopsis
    assert card.item.poster_url.startswith("https://")
    # Длительность серии в ответе не приходит вовсе: `episode_run_time` пуст
    # и у «Andor», и у «Чернобыля», а средняя стоит запроса на каждый сезон.
    assert card.item.runtime is None


def test_series_cast_comes_from_aggregate_credits(fixture):
    """Обычный credits отдал бы последний сезон: один актёр против 302."""
    card = parse_series(fixture("tmdb/tv_detail.json"))

    actors = [one for one in card.people if one.role is PersonRole.ACTOR]
    assert len(actors) > 50


def test_showrunner_comes_from_created_by(fixture):
    card = parse_series(fixture("tmdb/tv_detail.json"))

    assert [one for one in card.people if one.role is PersonRole.SHOWRUNNER]


def test_series_people_carry_the_identity_too(fixture):
    """У сериала состав приходит из другого блока ответа, чем у фильма, —
    сторожить заполнение идентичности надо отдельно."""
    card = parse_series(fixture("tmdb/tv_detail.json"))

    assert card.people
    for credit in card.people:
        assert credit.source is Source.TMDB, credit.name
        assert credit.source_id and credit.source_id.isdigit(), credit.name


def test_series_imdb_id_comes_from_the_appended_block(fixture):
    """У сериала на верхнем уровне `imdb_id` нет вовсе — он в external_ids, и
    без него не спросить ни MDBList, ни OMDB, ни Кинопоиск."""
    card = parse_series(fixture("tmdb/tv_detail.json"))

    imdb = [one for one in card.external_ids if one.source == "imdb"]
    assert imdb and imdb[0].value.startswith("tt")


def test_series_titles_come_from_their_own_fields(fixture):
    card = parse_series(fixture("tmdb/tv_detail.json"))

    assert card.item.title
    assert card.item.original_title
    assert card.item.year == 2022


def test_the_series_original_title_is_not_the_translated_one():
    """У «Andor» оба названия совпадают, и на нём перепутанные местами поля
    ненаблюдаемы вовсе — отсюда выдуманное тело с разными названиями."""
    payload = {
        "id": 1, "name": "Тьма", "original_name": "Dark",
        "aggregate_credits": {"cast": []},
    }

    card = parse_series(payload)

    assert card.item.title == "Тьма"
    assert card.item.original_title == "Dark"


def test_typo_in_append_to_response_is_caught_by_content(fixture):
    """Ответ приходит с 200 и просто без блока. Не поймать это здесь —
    значит записать карточку без состава и не узнать об этом никогда."""
    with pytest.raises(Incomplete):
        parse_movie(fixture("tmdb/movie_detail_typo_append.json"))


def test_a_series_without_its_appended_block_is_incomplete_too(fixture):
    """Довесок у сериала другой, и опечатка в нём — такая же тихая."""
    payload = {
        key: value
        for key, value in fixture("tmdb/tv_detail.json").items()
        if key != "aggregate_credits"
    }

    with pytest.raises(Incomplete):
        parse_series(payload)


def test_a_block_that_came_without_its_cast_is_incomplete(fixture):
    """Блок может приехать и обрезанным — с одними титрами и без актёров.
    Проверять только его наличие значит записать карточку без состава."""
    payload = dict(fixture("tmdb/movie_detail.json"))
    payload["credits"] = {"crew": []}

    with pytest.raises(Incomplete):
        parse_movie(payload)


def test_a_genuinely_empty_cast_is_not_incomplete(fixture):
    """Блок есть, он пуст — источник отдал всё, что имел. У документалки так
    и бывает, и такая карточка обязана сохраниться, а не застрять навсегда."""
    payload = dict(fixture("tmdb/movie_detail.json"))
    payload["credits"] = {"cast": [], "crew": []}

    assert parse_movie(payload).people == ()


async def test_client_requests_credits_for_a_movie(fixture):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json=fixture("tmdb/movie_detail.json"))

    client = TmdbClient(
        SourceHttp("tmdb", transport=httpx.MockTransport(handler)), api_key="k"
    )
    result = await client.card("157336", Kind.MOVIE)
    await client.aclose()

    assert isinstance(result, Found)
    assert result.value.item.source_id == "157336"
    assert "/movie/157336" in seen["url"]
    assert "credits" in seen["url"]
    assert "aggregate_credits" not in seen["url"]


async def test_client_requests_aggregate_credits_for_a_series(fixture):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json=fixture("tmdb/tv_detail.json"))

    client = TmdbClient(
        SourceHttp("tmdb", transport=httpx.MockTransport(handler)), api_key="k"
    )
    result = await client.card("83867", Kind.SERIES)
    await client.aclose()

    assert isinstance(result, Found)
    assert result.value.item.kind is Kind.SERIES
    assert "/tv/83867" in seen["url"]
    assert "aggregate_credits" in seen["url"]
    assert "external_ids" in seen["url"]


async def test_incomplete_answer_is_a_refusal_not_a_card(fixture):
    """Неполный ответ нельзя записать: карточка осталась бы «полной» без
    состава. Возвращаем отказ и повторим при следующем показе."""
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200, json=fixture("tmdb/movie_detail_typo_append.json")
        )
    )
    client = TmdbClient(SourceHttp("tmdb", transport=transport), api_key="k")

    result = await client.card("157336", Kind.MOVIE)
    await client.aclose()

    assert isinstance(result, Refusal)
    assert result.reason is Reason.BROKEN


def test_the_cheap_request_brings_only_the_counts(fixture):
    """167 КБ довеска ради двух чисел — это и есть причина отдельного метода."""
    counts = parse_series_counts(fixture("tmdb/tv_detail.json"))

    # Значения, а не «не пусто»: у «Andor» их два и двадцать четыре, и обмен
    # сезонов с сериями местами проверку на непустоту прошёл бы насквозь.
    assert (counts.seasons, counts.episodes) == (2, 24)


async def test_the_cheap_request_asks_without_appendages():
    asked = []

    def handler(request):
        asked.append(str(request.url))
        return httpx.Response(200, json={"number_of_seasons": 2,
                                         "number_of_episodes": 24})

    client = TmdbClient(
        SourceHttp("tmdb", transport=httpx.MockTransport(handler)), api_key="k"
    )

    result = await client.series_counts("83867")
    await client.aclose()

    assert result.value == SeriesCounts(seasons=2, episodes=24)
    assert "/tv/83867" in asked[0]
    assert "append_to_response" not in asked[0]


async def test_the_cheap_request_survives_a_dead_network():
    """`SourceHttp.get` отдаёт отказ вместо ответа — ветка, до которой
    `MockTransport` с готовым телом не доводит никогда."""

    def dead(request):
        raise httpx.ConnectError("сети нет", request=request)

    client = TmdbClient(
        SourceHttp("tmdb", transport=httpx.MockTransport(dead)), api_key="k"
    )

    result = await client.series_counts("83867")
    await client.aclose()

    assert isinstance(result, Refusal)
    assert result.reason is Reason.NETWORK


async def test_a_rate_limit_on_the_cheap_request_trips_the_breaker():
    """Перезапрос идёт по видимым карточкам: без отката он будет долбиться в 429
    на каждой прокрутке."""
    http = SourceHttp("tmdb", transport=httpx.MockTransport(
        lambda request: httpx.Response(429, json={"status_code": 25})
    ))
    client = TmdbClient(http, api_key="k")

    result = await client.series_counts("83867")
    await client.aclose()

    assert isinstance(result, Refusal)
    assert result.reason is Reason.RATE
    assert http.breaker.is_open()


async def test_a_broken_body_of_the_cheap_request_is_a_refusal():
    """Ответ 200 с телом не тем, что обещано, — отказ, а не пустые числа."""
    client = TmdbClient(
        SourceHttp("tmdb", transport=httpx.MockTransport(
            lambda request: httpx.Response(200, text="это не json")
        )),
        api_key="k",
    )

    result = await client.series_counts("83867")
    await client.aclose()

    assert isinstance(result, Refusal)
    assert result.reason is Reason.BROKEN
