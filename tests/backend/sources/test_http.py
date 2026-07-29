import logging
from datetime import timedelta

import httpx
import pytest

from backend.sources.errors import Reason, Refusal
from backend.sources.http import USER_AGENT, Breaker, SourceHttp
from tests.backend.sources.conftest import FakeClock


def capture() -> tuple[httpx.MockTransport, list[httpx.Request]]:
    """Запоминает ушедшее на провод: проверять надо запрос, а не намерение."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={})

    return httpx.MockTransport(handler), seen


async def test_user_agent_is_always_sent():
    """Без него Cloudflare не пускает запрос до MDBList вовсе."""
    transport, seen = capture()

    http = SourceHttp("mdblist", transport=transport)
    await http.get("https://api.mdblist.com/imdb/movie/tt0816692")
    await http.aclose()

    # httpx приводит имена заголовков к нижнему регистру.
    assert seen[0].headers["user-agent"] == USER_AGENT
    assert seen[0].headers["user-agent"], "пустое представление Cloudflare не примет"


async def test_request_goes_by_get_to_the_address_it_was_given():
    """Адрес и метод — это и есть запрос: `POST` вместо `GET` даёт 405, лишний
    слэш в пути — 404, и оба неотличимы от «источник ничего не знает»."""
    transport, seen = capture()

    http = SourceHttp("tmdb", transport=transport)
    await http.get("https://api.themoviedb.org/3/movie/157336")
    await http.aclose()

    assert seen[0].method == "GET"
    assert str(seen[0].url) == "https://api.themoviedb.org/3/movie/157336"


async def test_waiting_has_a_limit_on_every_leg_of_the_request():
    """Своего срока нет — httpx ждёт впятеро меньше, и медленный источник
    станет отказом на ровном месте. Каналов четыре, и обрезанный `connect`
    рвёт связь ровно так же, как обрезанный `read`."""
    transport, seen = capture()

    http = SourceHttp("omdb", transport=transport, timeout=1.5)
    await http.get("https://www.omdbapi.com/")
    await http.aclose()

    assert seen[0].extensions["timeout"] == {
        "connect": 1.5, "read": 1.5, "write": 1.5, "pool": 1.5,
    }


async def test_unnamed_timeout_is_the_generous_one():
    """Срок по умолчанию — двадцать секунд, а не пять: своего клиенты не
    называют, а на пяти отказом станет всякий, кто задумался."""
    transport, seen = capture()

    http = SourceHttp("gog", transport=transport)
    await http.get("https://catalog.gog.com/v1/catalog")
    await http.aclose()

    assert seen[0].extensions["timeout"]["read"] == 20.0


async def test_query_parameters_reach_the_wire_and_stay_with_their_request():
    """Ими задаётся весь запрос — от ключа до искомого названия. Осев в
    клиенте, поисковая строка уехала бы следом за карточкой."""
    transport, seen = capture()

    http = SourceHttp("tmdb", transport=transport)
    await http.get("https://api.themoviedb.org/3/search/movie",
                   params={"query": "Интерстеллар", "page": 2})
    await http.get("https://api.themoviedb.org/3/movie/157336")
    await http.aclose()

    assert seen[0].url.params["query"] == "Интерстеллар"
    assert seen[0].url.params["page"] == "2"
    assert "query" not in seen[1].url.params


async def test_request_headers_join_the_common_ones_without_settling_in():
    """Ключ Кинопоиска ездит заголовком, и общий `User-Agent` он не отменяет.
    А осев в клиенте, он уехал бы и в следующий запрос."""
    transport, seen = capture()

    http = SourceHttp("kinopoisk", transport=transport)
    await http.get("https://kinopoiskapiunofficial.tech/api/v2.2/films/258687",
                   headers={"X-API-KEY": "not-a-real-key"})
    await http.get("https://kinopoiskapiunofficial.tech/api/v2.2/films/1")
    await http.aclose()

    assert seen[0].headers["x-api-key"] == "not-a-real-key"
    assert seen[0].headers["user-agent"] == USER_AGENT
    assert "x-api-key" not in seen[1].headers
    assert seen[1].headers["user-agent"] == USER_AGENT


async def test_answer_behind_a_redirect_is_still_reached():
    """Остановившись на 302, клиент решил бы, что источник ничего не отдал."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path == "/v1/catalog":
            return httpx.Response(
                302, headers={"Location": "https://catalog.gog.com/v1/games"}
            )
        return httpx.Response(200, json={"ok": True})

    http = SourceHttp("gog", transport=httpx.MockTransport(handler))
    result = await http.get("https://catalog.gog.com/v1/catalog")
    await http.aclose()

    assert isinstance(result, httpx.Response)
    assert result.json() == {"ok": True}
    assert [request.url.path for request in seen] == ["/v1/catalog", "/v1/games"]


async def test_network_failure_becomes_a_refusal_not_an_exception(caplog):
    """Сбой не пишется в базу, и через минуту от него не останется ничего:
    запись в лог — единственное место, где он вообще был."""
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("нет сети", request=request)

    http = SourceHttp("tmdb", transport=httpx.MockTransport(handler))
    with caplog.at_level(logging.WARNING, logger="backend.sources.http"):
        result = await http.get("https://api.themoviedb.org/3/movie/157336")
    await http.aclose()

    assert isinstance(result, Refusal)
    assert result.reason is Reason.NETWORK
    assert result.source == "tmdb"
    assert "нет сети" in result.detail
    assert http.breaker.is_open() is False, "чужой чих — не повод молчать час"
    assert [record.levelno for record in caplog.records] == [logging.WARNING]
    assert "нет сети" in caplog.text


async def test_a_broken_client_is_not_dressed_up_as_a_network_failure():
    """Ловится только сетевое. Поймай `except` всё подряд — поломка разбора
    уехала бы наружу под видом «интернет барахлит»."""
    def handler(request: httpx.Request) -> httpx.Response:
        raise ValueError("это не сеть")

    http = SourceHttp("tmdb", transport=httpx.MockTransport(handler))
    with pytest.raises(ValueError):
        await http.get("https://api.themoviedb.org/3/movie/157336")
    await http.aclose()


async def test_timeout_becomes_a_refusal():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("долго", request=request)

    http = SourceHttp("gog", transport=httpx.MockTransport(handler))
    result = await http.get("https://catalog.gog.com/v1/catalog")
    await http.aclose()

    assert isinstance(result, Refusal)
    assert result.reason is Reason.NETWORK


def test_breaker_starts_closed():
    assert Breaker(FakeClock()).is_open() is False


def test_tripped_breaker_opens_and_then_heals():
    clock = FakeClock()
    breaker = Breaker(clock)

    breaker.trip(timedelta(hours=1))
    assert breaker.is_open() is True

    clock.advance(timedelta(minutes=59))
    assert breaker.is_open() is True

    # Ровно срок — это уже «можно»: секунду сверху пришлось бы ждать без причины.
    clock.advance(timedelta(minutes=1))
    assert breaker.is_open() is False


def test_the_breaker_reports_the_reason_it_was_tripped_for():
    """Взводят и по квоте, и по частоте. Отдавать всё время «квота» значит
    показывать человеку неверную причину и не давать её различить."""
    breaker = Breaker(FakeClock())

    breaker.trip(timedelta(minutes=1), Reason.RATE)
    assert breaker.reason is Reason.RATE

    # Не назвали причину — значит квота: остальные взводят, назвав её.
    breaker.trip(timedelta(hours=1))
    assert breaker.reason is Reason.QUOTA


def test_a_healed_breaker_can_be_tripped_again():
    """Отпустило, сходили, снова отказ — обычный день. Срок при этом новый:
    зажившее самоизлечение вернуло бы старый и открыло дверь сразу."""
    clock = FakeClock()
    breaker = Breaker(clock)

    breaker.trip(timedelta(hours=1))
    clock.advance(timedelta(hours=2))
    assert breaker.is_open() is False

    breaker.trip(timedelta(hours=1))
    assert breaker.is_open() is True

    clock.advance(timedelta(minutes=59))
    assert breaker.is_open() is True


async def test_open_breaker_stops_the_request_before_the_wire():
    """Отказ повторяет причину взвода: по частоте ждут минуту, по квоте сутки,
    и подменённая причина отправит человека ждать не тот срок."""
    transport, seen = capture()

    http = SourceHttp("omdb", transport=transport, clock=FakeClock())
    http.breaker.trip(timedelta(hours=2), Reason.RATE)

    result = await http.get("https://www.omdbapi.com/")
    await http.aclose()

    assert isinstance(result, Refusal)
    assert result.reason is Reason.RATE
    assert result.source == "omdb"
    assert seen == [], "запрос ушёл в сеть при взведённом предохранителе"


async def test_the_source_waits_by_its_own_clock_and_then_goes_again():
    """Часы внедряются, иначе тест ждал бы срок вживую. Подмени их
    системными — источник промолчит ровно столько же, но уже без спроса."""
    transport, seen = capture()
    clock = FakeClock()

    http = SourceHttp("omdb", transport=transport, clock=clock)
    http.breaker.trip(timedelta(hours=2))

    clock.advance(timedelta(hours=3))
    result = await http.get("https://www.omdbapi.com/")
    await http.aclose()

    assert isinstance(result, httpx.Response)
    assert len(seen) == 1


async def test_successful_response_comes_back_as_is():
    http = SourceHttp(
        "steam",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"ok": True})
        ),
    )
    result = await http.get("https://store.steampowered.com/api/appdetails")
    await http.aclose()

    assert isinstance(result, httpx.Response)
    assert result.json() == {"ok": True}


async def test_closing_really_closes_the_connections():
    """Закрытие не для порядка: соединения источника держит пул, и не закрыв
    его, приложение уйдёт с висящими сокетами. Видно по тому, что закрытым
    клиентом уже не сходить."""
    transport, seen = capture()

    http = SourceHttp("steam", transport=transport)
    await http.aclose()

    with pytest.raises(RuntimeError):
        await http.get("https://store.steampowered.com/api/appdetails")
    assert seen == []


async def test_error_codes_are_not_swallowed_here():
    """Классификация — дело клиента источника: коды у всех разные."""
    http = SourceHttp(
        "tmdb",
        transport=httpx.MockTransport(lambda request: httpx.Response(401)),
    )
    result = await http.get("https://api.themoviedb.org/3/movie/1")
    await http.aclose()

    assert isinstance(result, httpx.Response)
    assert result.status_code == 401
