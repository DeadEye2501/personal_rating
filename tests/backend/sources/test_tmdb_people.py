"""Фильмография человека и поиск человека по имени."""

import httpx

from backend.model import Found, GenreSource, Kind, Refusal, Source
from backend.sources.http import SourceHttp
from backend.sources.tmdb.client import TmdbClient
from backend.sources.tmdb.parse import parse_credits, parse_people
from tests.conftest import counting


def test_a_director_is_found_in_the_crew(fixture):
    """У режиссёра работы лежат в `crew`, и разбор обязан их видеть."""
    hits = parse_credits(fixture("tmdb/person_credits_movie.json"), Kind.MOVIE)

    assert "Начало" in [hit.title for hit in hits]


def test_an_actor_is_found_in_the_cast(fixture):
    """У актёра — в `cast`. Разбирать один список значило бы потерять половину
    людей: замерено, у Мёрфи 70 актёрских работ и 9 в съёмочной группе."""
    hits = parse_credits(fixture("tmdb/person_credits_actor.json"), Kind.MOVIE)

    assert "Тёмный рыцарь" in [hit.title for hit in hits]


def test_a_work_carries_everything_a_candidate_needs(fixture):
    """Замерено: строка фильмографии по составу полей совпадает с выдачей
    поиска. Перестань это быть правдой — карточки поедут без жанров, и фильтр
    по жанру спрячет их целиком."""
    hits = parse_credits(fixture("tmdb/person_credits_movie.json"), Kind.MOVIE)
    hit = next(one for one in hits if one.title == "Начало")

    assert hit.source is Source.TMDB
    assert hit.kind is Kind.MOVIE
    assert isinstance(hit.source_id, str) and hit.source_id.isdigit()
    assert hit.original_title and hit.original_title != hit.title
    assert hit.year
    assert hit.poster_url
    assert hit.synopsis
    assert hit.source_rating
    assert hit.genre_ext_ids
    assert all(space is GenreSource.TMDB and ext_id.isdigit()
               for space, ext_id in hit.genre_ext_ids)


def test_the_same_work_is_not_returned_twice(fixture):
    """Человек бывает на карточке и режиссёром, и продюсером — это две строки
    `crew` и одна работа."""
    hits = parse_credits(fixture("tmdb/person_credits_movie.json"), Kind.MOVIE)
    ids = [hit.source_id for hit in hits]

    assert len(ids) == len(set(ids))


def test_two_works_with_one_name_are_two_works():
    """Повторы снимаются по номеру работы, а не по названию: ремейк и оригинал
    у одного продюсера — обычное дело, и одна из двух карточек молча пропала бы.

    Тело рукописное: в записанном ответе пары с общим названием нет, а без неё
    ключ по названию неотличим от ключа по номеру."""
    payload = {"cast": [{"id": 1, "title": "Дюна", "release_date": "1984-12-14"},
                        {"id": 2, "title": "Дюна", "release_date": "2021-09-15"}]}

    hits = parse_credits(payload, Kind.MOVIE)

    assert [hit.source_id for hit in hits] == ["1", "2"]


def test_a_series_reads_its_own_field_names(fixture):
    """У сериалов название лежит в `name`, а дата — в `first_air_date`.
    Прочитай их по-киношному — получишь пустые названия при 200 в ответе."""
    hits = parse_credits(fixture("tmdb/person_credits_tv.json"), Kind.SERIES)

    assert hits
    assert all(hit.title for hit in hits)
    assert all(hit.kind is Kind.SERIES for hit in hits)


def test_everyone_found_comes_back(fixture):
    """Отбора среди найденных нет: сколько строк в ответе, столько и кандидатов.
    Поиск у TMDB нечёткий, и на «Christopher Nolan» приезжает в том числе
    `Christopher Noland` — другая фамилия, и она тоже ответ."""
    payload = fixture("tmdb/search_person.json")

    found = parse_people(payload)

    assert [one.source_id for one in found] == [
        str(row["id"]) for row in payload["results"]
    ]
    assert "2526416" in [one.source_id for one in found]


async def test_nobody_found_is_not_a_refusal(replay):
    """Пустая выдача — не событие: источник ответил, просто такого у него нет.

    Через клиент, а не через разбор: у `parse_people` путей к отказу нет вовсе,
    и на голом разборе это утверждение проверить нечем. Собирает отказ `parsed`
    в `_taken` — вот его и спрашиваем."""
    transport, _ = counting(replay("tmdb/search_person_empty.json"))
    client = TmdbClient(SourceHttp("tmdb", transport=transport), api_key="k")

    outcome = await client.find_people("никого такого нет")
    await client.aclose()

    assert outcome == Found([])


async def test_the_client_asks_the_movie_door(replay):
    transport, sent = counting(replay("tmdb/person_credits_movie.json"))
    client = TmdbClient(SourceHttp("tmdb", transport=transport), api_key="k")

    outcome = await client.credits_of("525", Kind.MOVIE)
    await client.aclose()

    assert isinstance(outcome, Found)
    assert "/person/525/movie_credits" in str(sent[0].url)


async def test_the_client_asks_the_series_door(replay):
    """У сериалов своя ручка: спроси киношную — получишь фильмы вместо
    сериалов, и оба ответа выглядят одинаково успешными."""
    transport, sent = counting(replay("tmdb/person_credits_tv.json"))
    client = TmdbClient(SourceHttp("tmdb", transport=transport), api_key="k")

    await client.credits_of("525", Kind.SERIES)
    await client.aclose()

    assert "/person/525/tv_credits" in str(sent[0].url)


async def test_the_filmography_takes_one_request(replay):
    """Порций у неё нет: TMDB отдаёт её целиком, и второй запрос значил бы, что
    мы их выдумали.

    Сегодняшнюю реализацию тест не проверяет — строки, дающей второй запрос, в
    ней нет; он сторожит **добавленную** порционность, как второй ключ
    сортировки библиотеки сторожит смену планировщика."""
    transport, sent = counting(replay("tmdb/person_credits_movie.json"))
    client = TmdbClient(SourceHttp("tmdb", transport=transport), api_key="k")

    await client.credits_of("525", Kind.MOVIE)
    await client.aclose()

    assert len(sent) == 1


async def test_a_broken_body_refuses_instead_of_raising():
    """Наружу из клиента исключений не летит: отказ — это значение."""
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"cast": [{"нет": "полей"}]})
    )
    client = TmdbClient(SourceHttp("tmdb", transport=transport), api_key="k")

    outcome = await client.credits_of("525", Kind.MOVIE)
    await client.aclose()

    assert isinstance(outcome, Refusal)


async def test_the_person_search_asks_by_name(replay):
    transport, sent = counting(replay("tmdb/search_person.json"))
    client = TmdbClient(SourceHttp("tmdb", transport=transport), api_key="k")

    outcome = await client.find_people("Christopher Nolan")
    await client.aclose()

    assert isinstance(outcome, Found)
    assert "/search/person" in str(sent[0].url)
    assert "Christopher" in str(sent[0].url)
