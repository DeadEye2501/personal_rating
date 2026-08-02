"""Кинопоиск: два зеркала под одним именем, и телу здесь верить нельзя."""

from datetime import timedelta

import httpx
import pytest

from backend.model import Found, IdSource, Kind, Missing, RatingSource, Reason, Refusal
from backend.sources.http import SourceHttp
from backend.sources.ratings.kinopoisk.client import KinopoiskClient
from backend.sources.ratings.kinopoisk.poiskkino import PoiskkinoClient
from backend.sources.ratings.kinopoisk.unofficial import UnofficialClient
from tests.conftest import FakeClock, counting, responding


def primary(transport) -> PoiskkinoClient:
    return PoiskkinoClient(SourceHttp("kinopoisk", transport=transport), api_key="k")


def fallback(transport) -> UnofficialClient:
    return UnofficialClient(SourceHttp("kinopoisk", transport=transport), api_key="k")


async def test_primary_reads_the_rating(replay):
    result = await primary(replay("kinopoisk/poiskkino_found.json")).ratings(
        "tt0816692", Kind.MOVIE
    )

    assert isinstance(result, Found)
    assert [one.source for one in result.value.values] == [RatingSource.KINOPOISK]
    assert result.value.values[0].value == 8.6


async def test_primary_hands_out_the_kinopoisk_identifier(replay):
    """Дальше по нему ходить дешевле, и сервис кладёт его в external_id."""
    result = await primary(replay("kinopoisk/poiskkino_found.json")).ratings(
        "tt0816692", Kind.MOVIE
    )

    ids = result.value.external_ids
    assert [one.source for one in ids] == [IdSource.KINOPOISK]
    assert ids[0].value == "258687"


async def test_primary_is_classified_by_http_code_not_by_the_body(replay, meta):
    """В их спецификации у 404 указан тип ошибки 403, и текст под кодом врёт.
    Поэтому верим коду ответа, а не числу в теле."""
    assert meta("kinopoisk/poiskkino_not_found.json")["status"] == 404

    result = await primary(replay("kinopoisk/poiskkino_not_found.json")).ratings(
        "tt0000000", Kind.MOVIE
    )

    assert isinstance(result, Missing)


async def test_a_quota_body_under_a_404_is_still_an_absence():
    """Ровно тот случай, ради которого правило и заведено: тело говорит про
    лимит, код — про отсутствие, и прав код."""
    transport = responding(404, json={"statusCode": 403, "message": "Превышен дневной лимит!"})

    result = await primary(transport).ratings("tt0000000", Kind.MOVIE)

    assert isinstance(result, Missing)


async def test_primary_quota_is_a_refusal_and_trips_the_breaker(replay, meta):
    assert meta("kinopoisk/poiskkino_quota.json")["status"] == 403
    client = primary(replay("kinopoisk/poiskkino_quota.json"))

    first = await client.ratings("tt0816692", Kind.MOVIE)
    second = await client.ratings("tt0111161", Kind.MOVIE)

    assert isinstance(first, Refusal)
    assert first.reason is Reason.QUOTA
    assert first.source == "kinopoisk"
    assert first.retry_after == timedelta(hours=6)
    assert isinstance(second, Refusal)
    assert second.detail == "предохранитель взведён"


async def test_primary_bad_key_is_a_refusal():
    transport = responding(
        401, json={"statusCode": 401, "message": "Пользователь не найден!"}
    )

    result = await primary(transport).ratings("tt0816692", Kind.MOVIE)

    assert isinstance(result, Refusal)
    assert result.reason is Reason.KEY


async def test_a_bad_key_does_not_close_the_source():
    """Битый ключ сроком не лечится: закрыв Кинопоиск на шесть часов, мы не
    дали бы человеку и шанса вписать новый."""
    transport, seen = counting(responding(401, json={"statusCode": 401}))

    client = primary(transport)
    await client.ratings("tt0816692", Kind.MOVIE)
    await client.ratings("tt0111161", Kind.MOVIE)

    assert len(seen) == 2


async def test_primary_rate_limit_trips_the_breaker_too():
    """Свалившись в поломку, частота не взвела бы предохранитель — и на каждый
    такой ответ мы дёргали бы запасное зеркало, тратя его суточные пятьсот."""
    transport, seen = counting(responding(429, json={"statusCode": 429}))

    client = primary(transport)
    first = await client.ratings("tt0816692", Kind.MOVIE)
    await client.ratings("tt0111161", Kind.MOVIE)

    assert first.reason is Reason.RATE
    assert first.source == "kinopoisk"
    assert first.retry_after == timedelta(minutes=1)
    assert len(seen) == 1
    # Второй ответ собирает уже предохранитель, из запомненной причины: без
    # `Reason.RATE` при взводе он сказал бы «кончилась суточная квота» — а квота у
    # Кинопоиска шесть часов против минуты, и человек ждал бы напрасно.
    second = await client.ratings("tt0068646", Kind.MOVIE)
    assert (second.reason, second.detail) == (Reason.RATE, "предохранитель взведён")


async def test_the_verdict_on_a_refusal_does_not_look_into_the_body(replay):
    """Записанный 403, у которого `message` приехало массивом, хотя схема
    источника обещает строку.

    Отсюда и проверка: код классифицируется кодом, в тело классификация не
    смотрит. Начни она искать в `message` подстроку — на массиве сломалась бы, и
    исчерпанная квота уехала бы в поломку либо исключением наружу. Второй
    квотный тест берёт другую запись, с телом обычной формы."""
    result = await primary(replay("kinopoisk/poiskkino_message_list.json")).ratings(
        "tt0816692", Kind.MOVIE
    )

    assert isinstance(result, Refusal)
    assert (result.source, result.reason) == ("kinopoisk", Reason.QUOTA)


async def test_primary_survives_a_json_array():
    result = await primary(responding(200, json=[1, 2])).ratings("tt0816692", Kind.MOVIE)

    assert isinstance(result, Refusal)
    assert result.reason is Reason.BROKEN


async def test_only_the_first_row_of_the_answer_is_read():
    """Зеркала отдают список, а нам нужен один фильм — первый, самый релевантный.
    С одной строкой в ответе «первая» и «последняя» неразличимы, поэтому здесь их
    две и оценки у них разные."""
    transport = responding(200, json={"docs": [
        {"id": 258687, "rating": {"kp": 8.6}},
        {"id": 999999, "rating": {"kp": 3.1}},
    ]})

    result = await primary(transport).ratings("tt0816692", Kind.MOVIE)

    assert result.value.values[0].value == 8.6
    assert [one.value for one in result.value.external_ids] == ["258687"]


async def test_the_identifier_survives_a_film_without_a_rating():
    """Фильм нашёлся, оценки у него нет — это ответ, а не «не знаю». Вернуть
    отсюда Missing значит выбросить добытый идентификатор Кинопоиска, ради
    которого мы сюда и ходим."""
    transport = responding(200, json={"docs": [{"id": 258687, "rating": {"kp": None}}]})

    result = await primary(transport).ratings("tt0816692", Kind.MOVIE)

    assert isinstance(result, Found)
    assert result.value.values == ()
    assert result.value.external_ids


async def test_an_empty_answer_from_the_primary_is_an_absence():
    result = await primary(responding(200, json={"docs": []})).ratings(
        "tt0000000", Kind.MOVIE
    )

    assert isinstance(result, Missing)


async def test_a_page_from_the_proxy_is_not_a_negative_fact():
    """404 без JSON — это не «фильма нет». Перед Кинопоиском стоит Envoy, и
    его страница под 404 приходит текстом; принять её за отрицательный факт
    значит записать в базу ложь на неделю."""
    transport = httpx.MockTransport(
        lambda request: httpx.Response(404, text="<html>404 Not Found</html>")
    )

    result = await primary(transport).ratings("tt0816692", Kind.MOVIE)

    assert isinstance(result, Refusal)
    assert result.reason is Reason.BROKEN


async def test_primary_asks_for_the_fields_it_needs():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(request.headers)
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"docs": []})

    await primary(httpx.MockTransport(handler)).ratings("tt0816692", Kind.MOVIE)

    # externalId и rating без selectFields в ответе не появятся.
    assert "externalId.imdb=tt0816692" in seen["url"]
    assert "selectFields=rating" in seen["url"]
    assert "selectFields=id" in seen["url"]
    assert seen["x-api-key"] == "k"


async def test_a_refusal_switches_to_the_fallback():
    asked = []

    def refuse(request: httpx.Request) -> httpx.Response:
        asked.append("primary")
        return httpx.Response(403, json={"statusCode": 403, "message": "лимит"})

    def answer(request: httpx.Request) -> httpx.Response:
        asked.append("fallback")
        return httpx.Response(
            200, json={"total": 1, "items": [{"ratingKinopoisk": 8.6}]}
        )

    client = KinopoiskClient(
        primary(httpx.MockTransport(refuse)), fallback(httpx.MockTransport(answer))
    )

    result = await client.ratings("tt0816692", Kind.MOVIE)
    await client.aclose()

    assert isinstance(result, Found)
    assert asked == ["primary", "fallback"]


async def test_an_honest_no_does_not_cost_a_second_request():
    asked = []

    def absent(request: httpx.Request) -> httpx.Response:
        asked.append("primary")
        return httpx.Response(404, json={"statusCode": 404})

    def never(request: httpx.Request) -> httpx.Response:
        asked.append("fallback")
        return httpx.Response(200, json={"total": 1, "items": []})

    client = KinopoiskClient(
        primary(httpx.MockTransport(absent)), fallback(httpx.MockTransport(never))
    )

    result = await client.ratings("tt0000000", Kind.MOVIE)
    await client.aclose()

    assert isinstance(result, Missing)
    assert asked == ["primary"]


async def test_a_found_answer_does_not_cost_a_second_request():
    asked = []

    def answer(request: httpx.Request) -> httpx.Response:
        asked.append("primary")
        return httpx.Response(200, json={"docs": [{"id": 1, "rating": {"kp": 8.6}}]})

    def never(request: httpx.Request) -> httpx.Response:
        asked.append("fallback")
        return httpx.Response(200, json={"total": 0, "items": []})

    client = KinopoiskClient(
        primary(httpx.MockTransport(answer)), fallback(httpx.MockTransport(never))
    )

    result = await client.ratings("tt0816692", Kind.MOVIE)
    await client.aclose()

    assert isinstance(result, Found)
    assert asked == ["primary"]


async def test_both_mirrors_refusing_leaves_a_refusal():
    """Отказ запасного и есть итог: выдумывать вместо него ответ нельзя."""
    client = KinopoiskClient(
        primary(responding(403, json={"statusCode": 403})),
        fallback(responding(402, json={"message": "Превышен лимит запросов"})),
    )

    result = await client.ratings("tt0816692", Kind.MOVIE)
    await client.aclose()

    assert isinstance(result, Refusal)
    assert result.reason is Reason.QUOTA


async def test_the_log_tells_which_mirror_failed_to_parse(caplog):
    """Наружу зеркала неразличимы нарочно — источник один, `kinopoisk`. Но в
    логе они различаться обязаны: искать неисправность придётся в одном из двух
    модулей, а по одинаковой записи не понять, в каком."""
    body = responding(200, text="<html>не json</html>")

    with caplog.at_level("WARNING"):
        assert isinstance(await primary(body).ratings("tt0816692", Kind.MOVIE),
                          Refusal)
        assert isinstance(await fallback(body).ratings("tt0816692", Kind.MOVIE),
                          Refusal)

    # Фраза привязывается к модулю, а не ищется в общем логе: логгеры у зеркал
    # разные, и обмен фраз местами набор в `caplog` не изменил бы — а свойство
    # («в каком из двух модулей искать неисправность») потерялось бы целиком.
    said = {record.name.rsplit(".", 1)[-1]: record.getMessage()
            for record in caplog.records if record.name.startswith("backend")}
    assert "основного зеркала" in said["poiskkino"]
    assert "запасного зеркала" in said["unofficial"]
    # И оба называют источник в самом тексте: подставляет его `parsed`, и
    # читается запись целиком, не заглядывая в имя логгера. Имя у зеркал общее
    # нарочно — наружу источник один.
    assert all(one.startswith("kinopoisk:") for one in said.values())


@pytest.mark.parametrize("mirror", ["primary", "fallback"])


async def test_a_well_formed_body_under_a_failure_code_is_not_an_answer(fixture, mirror):
    """Ответ разбирается только под кодом 200. Тело правильной формы под 5xx —
    обычное дело у периметра, который кеширует старую страницу, и разобрать его
    значило бы записать чужую оценку как свежую.

    Зеркала проверяются оба: проверка у них общая по форме, но написана порознь —
    `poiskkino.py` и `unofficial.py`, — и просевшая у одного по другому не
    видна."""
    bodies = {"primary": "kinopoisk/poiskkino_found.json",
              "fallback": "kinopoisk/unofficial_found.json"}
    client = primary if mirror == "primary" else fallback

    outcome = await client(
        responding(500, json=fixture(bodies[mirror]))
    ).ratings("tt0816692", Kind.MOVIE)

    assert isinstance(outcome, Refusal)
    assert outcome.reason is Reason.BROKEN


async def test_the_quota_closes_the_mirror_for_six_hours():
    """Срок — не украшение: у Кинопоиска квота самая жёсткая из всех, 500
    запросов в сутки, и минутный откат сжёг бы её на повторных отказах."""
    clock = FakeClock()
    http = SourceHttp(
        "kinopoisk", clock=clock, transport=responding(403, json={"statusCode": 403})
    )
    client = PoiskkinoClient(http, api_key="k")

    await client.ratings("tt0816692", Kind.MOVIE)
    clock.advance(timedelta(hours=5))
    assert http.breaker.is_open(), "предохранитель отпустил раньше срока"

    clock.advance(timedelta(hours=2))
    assert not http.breaker.is_open(), "предохранитель не отпустил через шесть часов"
    await client.aclose()
