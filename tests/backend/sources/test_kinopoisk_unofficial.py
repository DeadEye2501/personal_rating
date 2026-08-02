"""Запасное зеркало Кинопоиска: оценка, отказы и дозапрос карточки."""

from datetime import timedelta

import httpx

from backend.model import Found, Kind, Missing, RatingSource, Reason, Refusal
from backend.sources.http import SourceHttp
from backend.sources.ratings.kinopoisk.mirror import SOURCE
from backend.sources.ratings.kinopoisk.unofficial import UnofficialClient
from tests.conftest import counting, responding


def fallback(transport) -> UnofficialClient:
    return UnofficialClient(SourceHttp("kinopoisk", transport=transport), api_key="k")


async def test_fallback_empty_result_is_an_answer(replay):
    result = await fallback(replay("kinopoisk/unofficial_not_found.json")).ratings(
        "tt0000000", Kind.MOVIE
    )

    assert isinstance(result, Missing)


async def test_fallback_rating_comes_with_the_search(replay):
    """Одна оценка за один запрос: ratingKinopoisk лежит прямо здесь."""
    result = await fallback(replay("kinopoisk/unofficial_found.json")).ratings(
        "tt0816692", Kind.MOVIE
    )

    assert isinstance(result, Found)
    assert [one.source for one in result.value.values] == [RatingSource.KINOPOISK]
    assert result.value.values[0].value == 8.7
    # Тот же идентификатор, что у основного зеркала: источник один.
    assert [one.value for one in result.value.external_ids] == ["258687"]


async def test_fallback_asks_the_card_when_the_list_has_no_rating(replay):
    """Найдено пользователем 02.08.2026: у «Гражданина-мстителя» на сайте
    Кинопоиска 6.3, а в карточке приложения прочерк.

    Замерено живьём: в списке по `imdbId` оценки нет вовсе (`ratingKinopoisk:
    null`), а в карточке по номеру она есть. Клиент принимал это за честное «у
    источника такой оценки нет» и записывал пустое значение на неделю.

    Оба ответа записаны с живого API: у «Интерстеллара» оценка в списке стоит, и
    на нём этот случай не наблюдается вовсе."""
    result = await fallback(replay("kinopoisk/unofficial_list_without_rating.json",
                                   "kinopoisk/unofficial_card.json")).ratings(
        "tt35309713", Kind.MOVIE
    )

    assert isinstance(result, Found)
    assert [one.value for one in result.value.values] == [6.5]
    assert [one.value for one in result.value.external_ids] == ["6943602"]


async def test_fallback_asks_the_card_by_its_own_number(fixture):
    """Сторожим оба запроса разом: сперва список по `imdbId`, потом карточка по
    номеру из его же ответа.

    Записанные ответы раздаются по порядку и на адрес не смотрят — без этой
    проверки второй запрос мог бы уйти хоть по адресу первого, и набор остался
    бы зелёным. Тем же сторожем закрыт двухзапросный путь GOG."""
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url)
        body = fixture("kinopoisk/unofficial_list_without_rating.json") \
            if len(seen) == 1 else fixture("kinopoisk/unofficial_card.json")
        return httpx.Response(200, json=body)

    client = UnofficialClient(
        SourceHttp(SOURCE, transport=httpx.MockTransport(handler)), "k")
    await client.ratings("tt35309713", Kind.MOVIE)
    await client.aclose()

    assert len(seen) == 2, "карточку по номеру не спросили"
    assert seen[0].params["imdbId"] == "tt35309713"
    assert str(seen[1]).endswith("/films/6943602"), "номер взят не из ответа"


async def test_fallback_keeps_the_number_when_the_card_says_nothing(replay):
    """Карточка ответила, а оценки нет и там — бывает у свежих. Пустое значение
    тогда законно, но номер Кинопоиска обязан доехать: по нему на карточке
    зажигается ссылка на источник, и второй запрос не должен её отнимать."""
    result = await fallback(replay("kinopoisk/unofficial_list_without_rating.json",
                                   "kinopoisk/unofficial_not_found.json")).ratings(
        "tt35309713", Kind.MOVIE
    )

    assert isinstance(result, Found)
    assert result.value.values == ()
    assert [one.value for one in result.value.external_ids] == ["6943602"]


async def test_fallback_quota_has_its_own_code(replay, meta):
    """402 — отдельный код, не путать с 429 по частоте."""
    assert meta("kinopoisk/unofficial_quota.json")["status"] == 402

    result = await fallback(replay("kinopoisk/unofficial_quota.json")).ratings(
        "tt0816692", Kind.MOVIE
    )

    assert isinstance(result, Refusal)
    assert result.reason is Reason.QUOTA


async def test_fallback_html_from_nginx_does_not_crash_the_parser(replay, meta):
    """429 приходит от nginx с телом text/html — JSON на нём падает."""
    assert meta("kinopoisk/unofficial_rate.txt")["status"] == 429

    result = await fallback(replay("kinopoisk/unofficial_rate.txt")).ratings(
        "tt0816692", Kind.MOVIE
    )

    assert isinstance(result, Refusal)
    assert result.reason is Reason.RATE


async def test_fallback_rate_limit_trips_its_breaker_too():
    """Пять запросов в секунду — предел этой ручки. Не взведя предохранитель,
    мы продолжили бы стучаться и выбрали бы суточную квоту на отказы."""
    transport, seen = counting(responding(429, text="<html>429</html>"))

    client = fallback(transport)
    first = await client.ratings("tt0816692", Kind.MOVIE)
    await client.ratings("tt0111161", Kind.MOVIE)

    assert first.reason is Reason.RATE
    assert first.retry_after == timedelta(minutes=1)
    assert len(seen) == 1


async def test_fallback_bad_key_is_a_refusal(replay, meta):
    assert meta("kinopoisk/unofficial_bad_key.json")["status"] == 401

    result = await fallback(replay("kinopoisk/unofficial_bad_key.json")).ratings(
        "tt0816692", Kind.MOVIE
    )

    assert isinstance(result, Refusal)
    assert result.reason is Reason.KEY


async def test_fallback_sends_the_key_in_the_header_and_keeps_the_tt_prefix():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(request.headers)
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"total": 0, "items": []})

    await fallback(httpx.MockTransport(handler)).ratings("tt0816692", Kind.MOVIE)

    assert seen["x-api-key"] == "k"
    assert "imdbId=tt0816692" in seen["url"]
    # search-by-keyword не используем: у него 404 означает два разных смысла.
    assert "v2.2/films" in seen["url"]
    assert "search-by-keyword" not in seen["url"]


async def test_an_honest_zero_is_not_an_absence():
    """Весь план стоит на различии «нет ответа» и «ответ пустой». Ноль — это
    значение, а не молчание."""
    transport = responding(
        200, json={"total": 1, "items": [{"ratingKinopoisk": 0, "kinopoiskId": 1}]}
    )

    result = await fallback(transport).ratings("tt0816692", Kind.MOVIE)

    assert isinstance(result, Found)
    assert result.value.values[0].value == 0.0
