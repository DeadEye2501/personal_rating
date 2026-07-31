"""Steam: отсутствие игры приходит под кодом 200, а теги — вторым запросом."""

import json

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
from backend.sources.steam.parse import (
    parse_card,
    parse_search,
    parse_tags,
    poster_url,
)


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
    """Номера сверяются с записанным ответом, а не с их формой: у Steam рядом с
    `genres` лежат `categories`, они устроены так же и тоже нумерованы. Подмена
    ключа проходит проверку «цифры и пространство» молча, а в справочнике
    `steam:2` — это `Strategy`, тогда как `categories[2]` — «Одиночная игра»:
    каждая одиночная игра уехала бы в базу стратегией."""
    block = block_of(fixture("steam/appdetails.json"))
    card = parse_card(block)

    numbers = [ext_id for space, ext_id in card.genre_ext_ids
               if space is GenreSource.STEAM]

    # Сверяется равенство, и его хватает: в записанном ответе жанр один, а
    # категорий девятнадцать, так что подмена ключа роняет тест длиной. Отдельное
    # «не равно категориям» покраснеть не может никогда и потому не пишется.
    assert numbers == [str(one["id"]) for one in block["genres"]]


def test_tags_arrive_in_their_own_space(fixture):
    """Жанр и тег у Steam нумеруются порознь: `9` — это жанр «Гонки» и тег
    «Стратегия». Пространство обязано ехать вместе с номером, иначе стратегия
    молча получит гонки."""
    tags = parse_tags(fixture("steam/store_items.json"))

    assert tags
    assert all(
        space is GenreSource.STEAM_TAG and ext_id.isdigit() for space, ext_id in tags
    )


def test_a_tag_is_its_number_and_not_its_weight(fixture):
    """Номера тегов сверяются с записанным ответом: рядом с `tagid` в том же
    объекте лежит `weight`, тоже целое, и подмена одного другим проверку «цифры
    и пространство» проходит молча. В базу тогда уедут веса под видом номеров —
    и совпадут с чужими жанрами."""
    payload = fixture("steam/store_items.json")
    recorded = payload["response"]["store_items"][0]["tags"]

    numbers = [ext_id for _, ext_id in parse_tags(payload)]

    assert numbers == [str(one["tagid"]) for one in recorded]
    assert numbers != [str(one["weight"]) for one in recorded]


def test_an_answer_without_items_gives_no_tags(fixture):
    """На пустой ответ разбор обязан отдать пусто, а не упасть по индексу."""
    assert parse_tags(fixture("steam/store_items_empty.json")) == ()


async def test_the_card_carries_both_spaces(replay, fixture):
    """Клиент доливает теги к жанрам: без них у игры остаётся один-два общих
    жанра из двенадцати, какие есть у Steam на весь магазин."""
    appid = next(iter(fixture("steam/appdetails.json")))
    client = SteamClient(
        SourceHttp(
            "steam",
            transport=replay("steam/appdetails.json", "steam/store_items.json"),
        )
    )

    result = await client.card(appid, Kind.GAME)
    await client.aclose()

    assert isinstance(result, Found)
    spaces = {space for space, _ in result.value.genre_ext_ids}
    assert spaces == {GenreSource.STEAM, GenreSource.STEAM_TAG}


async def test_tags_that_did_not_arrive_do_not_break_the_card(
    replay, fixture, caplog
):
    """Отказ на тегах меняет карточку, а не роняет её: жанры уже собраны.

    Молчать при этом нельзя: карточка с одним жанром вместо двадцати выглядит
    исправной, и без записи в лог причину не найти никогда."""
    appid = next(iter(fixture("steam/appdetails.json")))
    client = SteamClient(
        SourceHttp(
            "steam",
            transport=replay("steam/appdetails.json", "steam/store_items_broken.txt"),
        )
    )

    with caplog.at_level("WARNING"):
        result = await client.card(appid, Kind.GAME)
    await client.aclose()

    assert isinstance(result, Found)
    assert {space for space, _ in result.value.genre_ext_ids} == {GenreSource.STEAM}
    assert "400" in caplog.text, "код отказа на тегах не записан"


async def test_a_hidden_game_gives_no_tags(fixture):
    """Скрытая из витрины приезжает без блока тегов вовсе — разбор обязан
    отдать пусто, а не споткнуться об отсутствующий ключ."""
    assert parse_tags(fixture("steam/store_items_missing.json")) == ()


async def test_the_tag_request_asks_the_way_that_answers(fixture):
    """`country_code: RU` отдаёт пустой ответ с `visible: false` — проверено
    живьём. Подменить его на RU значит молча лишить тегов все игры разом, и
    заметить это можно будет только по обеднённой карточке."""
    asked = []

    def handler(request: httpx.Request) -> httpx.Response:
        asked.append(request.url)
        if "appdetails" in str(request.url):
            return httpx.Response(200, json=fixture("steam/appdetails.json"))
        return httpx.Response(200, json=fixture("steam/store_items.json"))

    client = SteamClient(SourceHttp("steam", transport=httpx.MockTransport(handler)))
    await client.card("292030", Kind.GAME)
    await client.aclose()

    card_url, tags_url = asked
    assert "l=russian" in str(card_url), "карточка запрошена не по-русски"
    wanted = json.loads(tags_url.params["input_json"])
    assert wanted["context"]["country_code"] == "US"
    assert wanted["data_request"]["include_tag_count"] > 0
    assert wanted["ids"] == [{"appid": 292030}]


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
        seen["url"] = str(request.url)
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
        seen["url"] = str(request.url)
        return httpx.Response(200, json=fixture("steam/search.json"))

    client = SteamClient(SourceHttp("steam", transport=httpx.MockTransport(handler)))
    await client.search("Who's Your Daddy?!", Kind.GAME)
    await client.aclose()

    assert seen["url"].endswith("Who%27s%20Your%20Daddy%3F%21")


async def test_rate_limit_trips_the_breaker():
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(429, text="slow down")

    client = SteamClient(
        SourceHttp("steam", transport=httpx.MockTransport(handler))
    )
    first = await client.card("292030", Kind.GAME)
    await client.card("292030", Kind.GAME)
    await client.aclose()

    assert isinstance(first, Refusal)
    assert first.reason is Reason.RATE
    assert calls == 1, "второй запрос ушёл в сеть после 429"
