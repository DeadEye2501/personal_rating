"""Steam: отсутствие игры приходит под кодом 200, а теги — вторым запросом."""

import httpx

from backend.model import (
    CompanyRole,
    Found,
    GenreSource,
    Kind,
    Missing,
    RatingSource,
    Reason,
    Refusal,
    Source,
)
from backend.sources.http import SourceHttp
from backend.sources.steam.client import SteamClient
from backend.sources.steam.parse import parse_card, parse_search, poster_url
from tests.conftest import counting, responding


def block_of(payload: dict) -> dict:
    return next(iter(payload.values()))["data"]


def test_vertical_cover_uses_the_2x_name():
    """Имя файла без _2x врёт: он отдаёт 300×450 вместо заявленных 600×900."""
    url = poster_url("292030")

    assert url.endswith("library_600x900_2x.jpg")
    assert "292030" in url


def test_search_returns_candidates(fixture):
    hits = parse_search(fixture("steam/search.json"))

    assert hits
    assert hits[0].kind is Kind.GAME
    assert hits[0].source is Source.STEAM
    assert hits[0].source_id == "292030"
    assert hits[0].title
    assert hits[0].poster_url


def test_empty_search_is_an_empty_list(fixture):
    assert parse_search(fixture("steam/search_empty.json")) == []


def test_card_carries_both_studio_roles(fixture):
    """Обе роли доезжают до карточки. Привязка роли к студии здесь не
    проверяется и проверена быть не может: в записанном ответе разработчик и
    издатель — одна и та же студия, и обмен ключей местами набор пар не изменит.
    Сторожит привязку `test_convert.py:test_the_developer_is_not_the_publisher`,
    где имена нарочно разные."""
    card = parse_card(block_of(fixture("steam/appdetails.json")))

    roles = {company.role for company in card.companies}
    assert CompanyRole.DEVELOPER in roles
    assert CompanyRole.PUBLISHER in roles


def test_card_has_no_people(fixture):
    """Ни Steam, ни GOG людей не отдают — только компании."""
    assert parse_card(block_of(fixture("steam/appdetails.json"))).people == ()


def test_studios_come_without_any_identity(fixture):
    """Steam отдаёт названия студий голыми строками. Класть в идентичность
    нечего, и выдумывать суррогат незачем — таких склеивают по имени."""
    card = parse_card(block_of(fixture("steam/appdetails.json")))

    assert card.companies
    assert all(
        company.source is None and company.source_id is None
        for company in card.companies
    )


def test_metascore_belongs_to_metacritic(fixture):
    """У Valve лицензия с Metacritic, и число принадлежит им."""
    card = parse_card(block_of(fixture("steam/appdetails.json")))

    assert {one.source for one in card.ratings} == {RatingSource.METACRITIC}
    assert card.ratings[0].value == 93


def test_the_year_is_read_from_a_human_written_date(fixture):
    """Дата приходит строкой «18 мая. 2015 г.» — ни ISO, ни единого формата."""
    card = parse_card(block_of(fixture("steam/appdetails.json")))

    assert card.item.year == 2015


def test_a_game_not_yet_released_has_no_year():
    """У анонсированного в дате стоит «Coming soon» — года там нет вовсе."""
    data = {"steam_appid": 1, "name": "Скоро", "release_date": {"date": "Coming soon"}}

    assert parse_card(data).item.year is None


def test_a_game_from_the_last_century_keeps_its_year():
    """Ретро — половина причины, по которой магазина два: заметная часть его в
    Steam не продаётся. Год, отобранный только по двадцатым, потерял бы всё,
    что вышло до двухтысячного."""
    data = {"steam_appid": 1, "name": "Fallout", "release_date": {"date": "30 сен. 1997 г."}}

    assert parse_card(data).item.year == 1997


def test_genres_come_from_the_genres_and_not_from_the_neighbours(fixture):
    """Жанр берётся из `genres`, а не из соседей: рядом лежат `categories`, они
    устроены так же и тоже нумерованы. Подмена ключа проходит проверку «цифры и
    пространство» молча, а в записанном ответе жанр один против девятнадцати
    категорий — так что и длина, и значение тут говорят.

    Ждём `122`, а не `3`: жанр магазина едет номером тега-двойника, потому что
    пространство меток в справочнике одно. «Ролевая игра» у Steam — жанр `3` и
    тег `122`."""
    card = parse_card(block_of(fixture("steam/appdetails.json")))

    assert card.genre_ext_ids == ((GenreSource.STEAM, "122"),)


def test_a_genre_and_its_twin_tag_become_one_mark():
    """Жанр `1` «Экшены» и тег `19` «Экшен» — одна и та же метка справочника, и
    приходить она обязана одинаково обоими путями. Иначе игра, у которой Steam
    отдал жанр, а тегов не отдал, осталась бы без единого жанра."""
    block = {"steam_appid": 1, "name": "и", "genres": [{"id": "1"}]}

    assert parse_card(block).genre_ext_ids == ((GenreSource.STEAM, "19"),)


def test_a_genre_without_a_twin_is_dropped():
    """`23` «Инди» и `70` «Ранний доступ» жанра не несут, двойника у них нет, и
    в справочник они не едут вовсе: пропущенный сквозь него номер столкнулся бы
    с чужим тегом под тем же числом."""
    block = {"steam_appid": 1, "name": "и", "genres": [{"id": "23"}, {"id": "70"}]}

    assert parse_card(block).genre_ext_ids == ()


async def test_missing_game_answers_under_two_hundred(replay, meta):
    """`success: false` рядом с кодом 200 — это ответ, а не отказ: он не
    различает «appid не существует» и «существует, но скрыт из витрины»."""
    assert meta("steam/appdetails_missing.json")["status"] == 200
    client = SteamClient(
        SourceHttp("steam", transport=replay("steam/appdetails_missing.json"))
    )

    result = await client.card("999999999", Kind.GAME)
    await client.aclose()

    assert isinstance(result, Missing)


async def test_recorded_broken_request_is_a_refusal(replay, meta):
    """400 и телом `null` — разбор на нём падать не должен."""
    assert meta("steam/appdetails_broken.json")["status"] == 400
    client = SteamClient(
        SourceHttp("steam", transport=replay("steam/appdetails_broken.json"))
    )

    result = await client.card("мусор", Kind.GAME)
    await client.aclose()

    assert isinstance(result, Refusal)
    assert result.reason is Reason.BROKEN


async def test_a_reply_about_another_game_is_refused(fixture):
    """Иначе в базу уедет чужая карточка под видом запрошенной.

    Отказ должен быть замеченным, а не случайным: без сверки ключа разбор
    спотыкается о `None` и даёт тот же отказ, но с сообщением про атрибут — и
    настоящую причину потом не найти."""

    def handler(request: httpx.Request) -> httpx.Response:
        payload = fixture("steam/appdetails.json")
        return httpx.Response(200, json={"12345": next(iter(payload.values()))})

    client = SteamClient(SourceHttp("steam", transport=httpx.MockTransport(handler)))

    result = await client.card("292030", Kind.GAME)
    await client.aclose()

    assert isinstance(result, Refusal)
    assert result.reason is Reason.BROKEN
    assert "appid" in result.detail


async def test_success_without_data_is_a_refusal_not_a_crash():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"292030": {"success": True}})
    )
    client = SteamClient(SourceHttp("steam", transport=transport))

    result = await client.card("292030", Kind.GAME)
    await client.aclose()

    assert isinstance(result, Refusal)
    assert result.reason is Reason.BROKEN


async def test_search_answering_with_an_object_does_not_crash():
    """Разбор падает не только `ValueError`: на словаре вместо списка —
    `TypeError`, и наружу из клиента не должно вылетать ничего."""
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"unexpected": "shape"})
    )
    client = SteamClient(SourceHttp("steam", transport=transport))

    result = await client.search("что угодно", Kind.GAME)
    await client.aclose()

    assert isinstance(result, Refusal)
    assert result.reason is Reason.BROKEN


async def test_found_game_comes_back_as_a_card(replay):
    client = SteamClient(
        SourceHttp("steam", transport=replay("steam/appdetails.json"))
    )

    result = await client.card("292030", Kind.GAME)
    await client.aclose()

    assert isinstance(result, Found)
    assert result.value.item.kind is Kind.GAME
    assert result.value.item.source is Source.STEAM


async def test_search_uses_the_community_endpoint(fixture):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        # Первый, а не последний: за поиском идёт второй запрос — про род
        # товара, — и он в этих двух проверках не участвует.
        seen.setdefault("url", str(request.url))
        return httpx.Response(200, json=fixture("steam/search.json"))

    client = SteamClient(SourceHttp("steam", transport=httpx.MockTransport(handler)))
    await client.search("The Witcher 3 Wild Hunt", Kind.GAME)
    await client.aclose()

    # У магазинного storesearch длинные запросы дают ноль результатов.
    assert "steamcommunity.com/actions/SearchApps" in seen["url"]
    assert "storesearch" not in seen["url"]


async def test_a_query_with_url_punctuation_survives(fixture):
    """Строка поиска идёт частью пути: `?` и `#` там структурные, и «Who's
    Your Daddy?!» уехал бы обрезанным. Steam при этом ответит 200 и найдёт не
    то, что просили, — тихо неверная выдача вместо отказа."""
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.setdefault("url", str(request.url))
        return httpx.Response(200, json=fixture("steam/search.json"))

    client = SteamClient(SourceHttp("steam", transport=httpx.MockTransport(handler)))
    await client.search("Who's Your Daddy?!", Kind.GAME)
    await client.aclose()

    assert seen["url"].endswith("Who%27s%20Your%20Daddy%3F%21")


async def test_rate_limit_trips_the_breaker():
    transport, seen = counting(responding(429, text="slow down"))

    client = SteamClient(
        SourceHttp("steam", transport=transport)
    )
    first = await client.card("292030", Kind.GAME)
    await client.card("292030", Kind.GAME)
    await client.aclose()

    assert isinstance(first, Refusal)
    assert first.reason is Reason.RATE
    assert len(seen) == 1, "второй запрос ушёл в сеть после 429"
