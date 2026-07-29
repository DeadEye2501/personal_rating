"""Отказ TMDB отличается от «такого у меня нет» — и то, и другое от успеха."""

from datetime import timedelta

import httpx

from backend.model import Kind
from backend.sources.errors import Missing, Reason, Refusal
from backend.sources.http import SourceHttp
from backend.sources.tmdb.client import TmdbClient
from tests.backend.sources.conftest import FakeClock, responding


async def ask(transport: httpx.MockTransport):
    client = TmdbClient(SourceHttp("tmdb", transport=transport), api_key="k")
    result = await client.card("157336", Kind.MOVIE)
    await client.aclose()
    return result


async def test_recorded_missing_object_is_an_answer(replay, meta):
    """Тело и код берутся из записанного ответа, а не сочиняются здесь."""
    assert meta("tmdb/not_found.json")["status"] == 404

    assert isinstance(await ask(replay("tmdb/not_found.json")), Missing)


async def test_recorded_bad_key_is_a_refusal(replay, meta):
    assert meta("tmdb/bad_key.json")["status"] == 401

    result = await ask(replay("tmdb/bad_key.json"))

    assert isinstance(result, Refusal)
    assert result.reason is Reason.KEY


async def test_broken_identifier_is_also_an_answer():
    """Код 6 — «идентификатор битый». Для нас это то же «такого нет»."""
    assert isinstance(await ask(responding(404, json={"status_code": 6})), Missing)


async def test_rate_limit_is_a_refusal():
    result = await ask(responding(429, json={"status_code": 25}))

    assert isinstance(result, Refusal)
    assert result.reason is Reason.RATE
    assert result.retry_after is not None


async def test_revoked_key_is_a_refusal():
    result = await ask(responding(401, json={"status_code": 10}))

    assert isinstance(result, Refusal)
    assert result.reason is Reason.KEY


async def test_server_failures_are_refusals():
    for status in (500, 502, 503, 504):
        result = await ask(responding(status, json={"status_code": 11}))

        assert isinstance(result, Refusal), status
        assert result.reason is Reason.BROKEN, status


async def test_a_bad_key_beats_a_missing_object():
    """TMDB проверяет ключ раньше существования объекта: при протухшем ключе
    даже несуществующий id даёт 401. Тело при этом несёт код «не найдено» — и
    поверить телу значило бы записать «такого фильма нет» из-за своего же
    протухшего ключа.

    Утверждается исход, а не его отрицание: «не Missing» верно и для `Found` с
    мусором, и для любого неверного отказа, поэтому такой тест зеленел бы при
    полностью отсутствующей классификации."""
    result = await ask(responding(401, json={"status_code": 34}))

    assert isinstance(result, Refusal)
    assert result.reason is Reason.KEY
    assert result.source == "tmdb"


async def test_a_404_without_json_is_not_a_negative_fact():
    """Страница от прокси под 404 не должна стать авторитетным «такого нет»,
    которое потом неделю никто не перепроверит."""
    transport = httpx.MockTransport(
        lambda request: httpx.Response(404, text="<html>404 Not Found</html>")
    )

    result = await ask(transport)

    assert isinstance(result, Refusal)
    assert result.reason is Reason.BROKEN


async def test_a_404_with_an_unknown_status_code_is_not_a_negative_fact():
    result = await ask(responding(404, json={"status_code": 999}))

    assert isinstance(result, Refusal)
    assert result.reason is Reason.BROKEN


async def test_the_absence_code_alone_is_not_a_negative_fact():
    """«Не найдено» — это пара «404 и код в теле». Один код в теле под чужим
    HTTP-кодом отрицательным фактом не делает: поломка сервера записалась бы
    как «такого фильма нет» и прожила бы неделю."""
    result = await ask(responding(500, json={"status_code": 34}))

    assert isinstance(result, Refusal)
    assert result.reason is Reason.BROKEN


async def test_rate_limit_trips_the_breaker():
    """Иначе следующий показ ленты снова упрётся в тот же 429."""
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(429, json={"status_code": 25})

    client = TmdbClient(
        SourceHttp("tmdb", transport=httpx.MockTransport(handler)), api_key="k"
    )
    await client.card("157336", Kind.MOVIE)
    second = await client.card("83867", Kind.MOVIE)
    await client.aclose()

    assert isinstance(second, Refusal)
    assert calls == 1, "второй запрос ушёл в сеть после 429"


async def test_the_breaker_lets_go_when_the_backoff_has_passed():
    """Откат — минута, и это срок, а не украшение: поставь час, и после 429
    источник промолчал бы весь час, хотя TMDB готов отвечать через минуту."""
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(429, json={"status_code": 25})

    clock = FakeClock()
    client = TmdbClient(
        SourceHttp("tmdb", transport=httpx.MockTransport(handler), clock=clock),
        api_key="k",
    )
    await client.card("157336", Kind.MOVIE)
    clock.advance(timedelta(seconds=30))
    await client.card("83867", Kind.MOVIE)
    assert calls == 1, "предохранитель отпустил раньше срока"

    clock.advance(timedelta(seconds=31))
    await client.card("83867", Kind.MOVIE)
    await client.aclose()

    assert calls == 2, "предохранитель не отпустил через минуту"


async def test_the_tripped_breaker_keeps_the_reason_it_was_tripped_for():
    """Взводит частота, а не квота, и человеку показывается именно это."""
    client = TmdbClient(
        SourceHttp("tmdb", transport=responding(429, json={"status_code": 25})),
        api_key="k",
    )
    await client.card("157336", Kind.MOVIE)
    second = await client.card("83867", Kind.MOVIE)
    await client.aclose()

    assert second.reason is Reason.RATE


async def test_a_missing_object_does_not_trip_the_breaker():
    """«Такого нет» — обычный ответ. Закрыв на нём источник, приложение
    перестало бы искать после первого же промаха."""
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(404, json={"status_code": 34})

    client = TmdbClient(
        SourceHttp("tmdb", transport=httpx.MockTransport(handler)), api_key="k"
    )
    await client.card("157336", Kind.MOVIE)
    await client.card("83867", Kind.MOVIE)
    await client.aclose()

    assert calls == 2


async def test_search_classifies_the_same_way():
    """Классификация живёт в одном месте на оба метода: разойдясь, они дали бы
    «ключ протух» на карточке и «ничего не нашлось» в поиске одновременно."""
    client = TmdbClient(
        SourceHttp("tmdb", transport=responding(401, json={"status_code": 7})),
        api_key="k",
    )

    result = await client.search("что угодно", Kind.MOVIE)
    await client.aclose()

    assert isinstance(result, Refusal)
    assert result.reason is Reason.KEY
