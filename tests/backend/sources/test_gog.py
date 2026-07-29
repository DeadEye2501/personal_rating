"""GOG: поиск не умеет отвечать «не найдено», и отрицательный факт отсюда не
записывается никогда."""

import httpx

from backend.model import CompanyRole, GenreSource, Kind, RatingSource, Source
from backend.sources.errors import Found, Reason, Refusal
from backend.sources.gog.client import GogClient
from backend.sources.gog.parse import parse_catalog, to_hit
from backend.sources.http import SourceHttp


def answering(body) -> SourceHttp:
    return SourceHttp(
        "gog",
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=body)),
    )


def test_catalog_row_is_already_a_card(fixture):
    """Отдельный детальный запрос не нужен: всё нужное приходит сразу."""
    cards = parse_catalog(fixture("gog/catalog.json"))

    assert cards
    card = cards[0]
    assert card.item.kind is Kind.GAME
    assert card.item.source is Source.GOG
    assert card.item.source_id
    assert card.item.title
    assert card.item.poster_url


def test_the_cover_is_the_vertical_one(fixture):
    """В ответе две обложки, и горизонтальная в ленту не годится: карточки
    рисуются в 2:3, и подмена растянула бы её на весь ряд."""
    row = fixture("gog/catalog.json")["products"][0]

    card = parse_catalog(fixture("gog/catalog.json"))[0]

    assert card.item.poster_url == row["coverVertical"]
    assert card.item.poster_url != row["coverHorizontal"]


def test_the_year_is_read_from_a_dotted_date(fixture):
    """Дата приходит как `2023.08.03` — не ISO, но год стоит первым."""
    assert parse_catalog(fixture("gog/catalog.json"))[0].item.year == 2023


def test_genres_come_as_slugs(fixture):
    """У GOG идентификатор жанра — слаг, а не число. Сопоставляем по нему:
    в самом слаге у них опечатка, rougelike вместо roguelike."""
    cards = parse_catalog(fixture("gog/catalog.json"))

    marked = [pair for card in cards for pair in card.genre_ext_ids]
    assert marked, "жанры не разобраны"
    assert not any(slug.isdigit() for _space, slug in marked)
    # Оба пространства, а не одно: теги GOG приезжают тем же ответом.
    assert {space for space, _ in marked} == {GenreSource.GOG, GenreSource.GOG_TAG}


def test_a_genre_and_a_tag_with_the_same_slug_stay_apart(fixture):
    """`fantasy` у GOG — и жанр, и тег одновременно, и в справочнике это
    разные строки: слитые в одно пространство, они дали бы один жанр вместо
    двух разных соответствий."""
    card = parse_catalog(fixture("gog/catalog.json"))[0]

    assert (GenreSource.GOG, "fantasy") in card.genre_ext_ids
    assert (GenreSource.GOG_TAG, "fantasy") in card.genre_ext_ids


def test_developers_and_publishers_are_companies(fixture):
    cards = parse_catalog(fixture("gog/catalog.json"))

    roles = {one.role for card in cards for one in card.companies}
    assert CompanyRole.DEVELOPER in roles
    assert CompanyRole.PUBLISHER in roles


def test_studios_come_without_any_identity(fixture):
    """Как и у Steam: названия студий приходят голыми строками, класть в
    идентичность нечего. Таких склеивают по имени, и это законно."""
    cards = parse_catalog(fixture("gog/catalog.json"))

    studios = [one for card in cards for one in card.companies]
    assert studios
    assert all(
        one.source is None and one.source_id is None for one in studios
    )


def test_player_rating_belongs_to_gog(fixture):
    """Оценка игроков лежит в `reviewsRating`, а `ratings` у GOG — это
    возрастные рейтинги, PEGI и ESRB. Перепутать их значит записать «18» как
    оценку игры."""
    card = parse_catalog(fixture("gog/catalog.json"))[0]

    assert [one.source for one in card.ratings] == [RatingSource.GOG]
    # Как отдал источник: у GOG это десятые доли пятибалльной, 46 — это 4.6.
    assert card.ratings[0].value == 46


def test_a_game_nobody_reviewed_has_no_rating():
    """Ноль отзывов даёт ноль в `reviewsRating`, и записать его значило бы
    объявить игру худшей в каталоге."""
    payload = {"products": [{"id": 1, "title": "Никто не играл", "reviewsRating": 0}]}

    assert parse_catalog(payload)[0].ratings == ()


def test_a_card_folds_into_a_candidate(fixture):
    """Наружу поиск отдаёт кандидатов, как и остальные два магазина."""
    card = parse_catalog(fixture("gog/catalog.json"))[0]

    hit = to_hit(card)

    assert hit.source is Source.GOG
    assert hit.source_id == card.item.source_id
    assert hit.title == card.item.title
    assert hit.year == card.item.year
    assert hit.poster_url == card.item.poster_url
    assert hit.genre_ext_ids == card.genre_ext_ids
    assert hit.source_rating == card.ratings[0].value


def test_a_candidate_without_a_rating_carries_none(fixture):
    """Пустой список оценок — не повод падать по индексу."""
    card = parse_catalog({"products": [{"id": 1, "title": "Без оценки"}]})[0]

    assert to_hit(card).source_rating is None


async def test_search_never_reports_nothing_found(fixture):
    """На бессмыслицу приезжает 200 и десятки несвязанных игр. Значит Missing
    отсюда вернуть нельзя никогда — иначе мы запишем ложный отрицательный факт
    о существующей в каталоге игре."""
    client = GogClient(answering(fixture("gog/catalog_nonsense.json")))

    result = await client.search("zzqqxxnotagame123", Kind.GAME)
    await client.aclose()

    assert isinstance(result, Found)
    assert result.value, "фикстура бессмыслицы пуста — она должна быть непустой"


async def test_even_an_empty_catalog_answer_is_not_missing():
    client = GogClient(answering({"products": []}))

    result = await client.search("что угодно", Kind.GAME)
    await client.aclose()

    assert isinstance(result, Found)
    assert result.value == []


async def test_search_asks_the_catalog_the_way_that_answers(fixture):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json=fixture("gog/catalog.json"))

    client = GogClient(SourceHttp("gog", transport=httpx.MockTransport(handler)))
    await client.search("Baldur's Gate", Kind.GAME)
    await client.aclose()

    assert "catalog.gog.com/v1/catalog" in seen["url"]
    # Без `like:` каталог ищет точное совпадение и отвечает пустотой.
    assert "like%3ABaldur" in seen["url"]
    # Без локали жанры приезжают по-английски, а сопоставляем мы по слагам —
    # но описание и названия жанров в ответе нужны человеку на его языке.
    assert "locale=ru-RU" in seen["url"]


async def test_card_picks_the_asked_identifier(fixture):
    cards = parse_catalog(fixture("gog/catalog.json"))
    wanted = cards[1].item.source_id
    client = GogClient(answering(fixture("gog/catalog.json")))

    result = await client.card(wanted, Kind.GAME)
    await client.aclose()

    assert isinstance(result, Found)
    assert result.value.item.source_id == wanted


async def test_card_that_the_catalog_did_not_return_is_not_a_negative_fact(fixture):
    """Каталог не отдал запрошенный идентификатор — это отказ, а не «игры
    нет». Спрашиваем мы конкретный id, но спрашиваем у поиска по названию, а он
    отвечает чем-нибудь на что угодно. Записать отсюда Missing значит навсегда
    не дать добавить существующую игру."""
    client = GogClient(answering(fixture("gog/catalog.json")))

    result = await client.card("999999999", Kind.GAME)
    await client.aclose()

    assert isinstance(result, Refusal)
    assert result.reason is Reason.BROKEN


async def test_server_failure_is_a_refusal():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(503, text="Service Unavailable")
    )
    client = GogClient(SourceHttp("gog", transport=transport))

    result = await client.search("Baldur's Gate", Kind.GAME)
    await client.aclose()

    assert isinstance(result, Refusal)
    assert result.reason is Reason.BROKEN


async def test_rate_limit_trips_the_breaker():
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(429, text="slow down")

    client = GogClient(SourceHttp("gog", transport=httpx.MockTransport(handler)))
    first = await client.search("Baldur's Gate", Kind.GAME)
    await client.search("Baldur's Gate", Kind.GAME)
    await client.aclose()

    assert isinstance(first, Refusal)
    assert first.reason is Reason.RATE
    assert calls == 1, "второй запрос ушёл в сеть после 429"


async def test_non_json_body_does_not_crash_the_parser():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, text="<html>nope</html>")
    )
    client = GogClient(SourceHttp("gog", transport=transport))

    result = await client.search("Baldur's Gate", Kind.GAME)
    await client.aclose()

    assert isinstance(result, Refusal)
    assert result.reason is Reason.BROKEN


async def test_unexpected_shape_does_not_crash_the_parser():
    client = GogClient(answering({"products": "не список"}))

    result = await client.search("Baldur's Gate", Kind.GAME)
    await client.aclose()

    assert isinstance(result, Refusal)
