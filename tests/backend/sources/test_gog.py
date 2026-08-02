"""GOG: поиск не умеет отвечать «не найдено», и отрицательный факт отсюда не
записывается никогда."""

import httpx
import pytest

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
from backend.sources.gog.client import GogClient
from backend.sources.gog.parse import parse_catalog, to_hit
from backend.sources.http import SourceHttp
from tests.conftest import counting, responding, unreachable


def answering(body) -> SourceHttp:
    """Каталог GOG отвечает всегда — отсюда обёртка вокруг общей заготовки."""
    return SourceHttp("gog", transport=responding(json=body))


# Номер, под которым один и тот же продукт лежит в обеих записанных фикстурах:
# в товарной ручке с названием «Baldur's Gate 3» и в ответе каталога. Цепочка
# «номер → название → каталог» иначе не проверяется целиком.
WANTED = "1456460669"


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
    название GOG переводит, слаг нет."""
    cards = parse_catalog(fixture("gog/catalog.json"))

    marked = [pair for card in cards for pair in card.genre_ext_ids]
    assert marked, "жанры не разобраны"
    assert not any(slug.isdigit() for _space, slug in marked)
    # Пространство одно: жанры и теги GOG слиты решением пользователя.
    assert {space for space, _ in marked} == {GenreSource.GOG}


def test_a_genre_and_a_tag_with_the_same_slug_merge(fixture):
    """`fantasy` у GOG — и жанр, и тег одновременно, и в один список он входит
    один раз: «смешиваем их в один список, попутно убирая дубликаты»."""
    card = parse_catalog(fixture("gog/catalog.json"))[0]

    assert [slug for _space, slug in card.genre_ext_ids].count("fantasy") == 1


def test_both_spellings_of_one_mark_become_the_same_slug():
    """Одно и то же у GOG пишется по-разному в жанрах и в тегах: жанр
    `role-playing` и тег `point-and-click` в справочнике зовутся `rpg` и
    `pointandclick`. Без приведения сочетание `action` + `rpg` не сработало бы
    там, где ролевая приехала жанром."""
    payload = {
        "products": [
            {
                "id": 1,
                "title": "Baldur's Gate 3",
                "genres": [{"slug": "role-playing"}, {"slug": "roguelike"}],
                "tags": [{"slug": "point-and-click"}],
            }
        ]
    }

    marked = parse_catalog(payload)[0].genre_ext_ids

    assert [slug for _space, slug in marked] == [
        "rpg", "rougelike", "pointandclick"
    ]


def test_both_studio_roles_are_companies(fixture):
    """Обе роли доезжают до карточки. Привязка роли к студии здесь не
    проверяется и проверена быть не может: в записанном ответе разработчик и
    издатель — одна и та же студия, и обмен ключей местами набор пар не изменит.
    Сторожит привязку `test_convert.py:test_the_developer_is_not_the_publisher`,
    где имена нарочно разные."""
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


async def test_card_picks_the_asked_identifier(replay):
    """Номер приходит из выдачи поиска, и по нему собирается карточка. Ответы
    идут парой: сначала товарная ручка с названием, потом каталог."""
    client = GogClient(SourceHttp(
        "gog", transport=replay("gog/product.json", "gog/catalog.json")
    ))

    result = await client.card(WANTED, Kind.GAME)
    await client.aclose()

    assert isinstance(result, Found)
    assert result.value.item.source_id == WANTED


async def test_the_catalog_is_asked_by_title_and_never_by_number(fixture):
    """Сторожим оба запроса разом: сначала товарная ручка номером, потом каталог
    названием. Подстановка номера в каталог возвращает прежнюю поломку, при
    которой игру из GOG нельзя было добавить вовсе — почему именно название, а
    не слаг, замерено в докстринге `_title`."""
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url)
        body = fixture("gog/product.json") if len(seen) == 1 \
            else fixture("gog/catalog.json")
        return httpx.Response(200, json=body)

    client = GogClient(SourceHttp("gog", transport=httpx.MockTransport(handler)))
    await client.card(WANTED, Kind.GAME)
    await client.aclose()

    assert f"api.gog.com/products/{WANTED}" in str(seen[0])
    assert seen[1].host == "catalog.gog.com"
    # Сверяем разобранный параметр, а не строку адреса: как httpx кодирует
    # апостроф и пробел, к делу не относится.
    asked = seen[1].params["query"]
    assert asked == "like:Baldur's Gate 3", "каталог спрошен названием"
    assert WANTED not in asked, "номер в каталоге не находит ничего"


async def test_a_number_that_is_no_product_is_missing(replay):
    """У товарной ручки 404 — единственное честное «такого продукта нет» у GOG:
    поиск в каталоге сказать этого не умеет, а она умеет. Проверено живьём и
    записано в спеке отказов."""
    client = GogClient(SourceHttp(
        "gog", transport=replay("gog/product_missing.json")
    ))

    result = await client.card("999999999", Kind.GAME)
    await client.aclose()

    assert isinstance(result, Missing)


async def test_a_404_without_json_is_not_a_missing_product():
    """Тем же правилом, что у оценочных источников: страница вместо JSON под
    кодом 404 — это чужой периметр, а не «игры нет». Записанный отсюда
    отрицательный факт объявил бы существующую игру отсутствующей.

    Записанная фикстура товарной ручки отвечает честным JSON, и эту половину
    сторожит сосед; здесь проверяется вторая."""
    client = GogClient(SourceHttp("gog", transport=responding(404, text="<html>")))

    result = await client.card(WANTED, Kind.GAME)
    await client.aclose()

    assert isinstance(result, Refusal)
    assert result.reason is Reason.BROKEN


async def test_card_that_the_catalog_did_not_return_is_not_a_negative_fact(replay):
    """Товар есть, а каталог его не отдал — это отказ, а не «игры нет».
    Каталог отвечает чем-нибудь на что угодно, и записать отсюда Missing значит
    навсегда не дать добавить существующую игру."""
    client = GogClient(SourceHttp(
        "gog", transport=replay("gog/product.json", "gog/catalog_nonsense.json")
    ))

    result = await client.card(WANTED, Kind.GAME)
    await client.aclose()

    assert isinstance(result, Refusal)
    assert result.reason is Reason.BROKEN


async def test_a_broken_product_answer_does_not_crash_the_client():
    """Названия в ответе не оказалось — отказ, а не исключение через границу."""
    client = GogClient(answering({"id": 1456460669}))

    result = await client.card(WANTED, Kind.GAME)
    await client.aclose()

    assert isinstance(result, Refusal)
    assert result.reason is Reason.BROKEN


@pytest.mark.parametrize("title", [None, ""])
async def test_a_product_without_a_usable_title_is_a_refusal(title):
    """Пустое название и `null` — неразобранный ответ, а не название. Пустым
    запросом каталог понимает буквально: отдаёт весь каталог, шесть с лишним
    тысяч наименований, и нужного там может не оказаться на первой странице —
    то есть «каталог не вернул игру» вместо честного отказа.

    Пропавший ключ этой ветки не проверяет: он ронял разбор и до неё."""
    client = GogClient(answering({"id": 1456460669, "title": title}))

    result = await client.card(WANTED, Kind.GAME)
    await client.aclose()

    assert isinstance(result, Refusal)
    assert result.reason is Reason.BROKEN


async def test_a_product_endpoint_failure_is_a_refusal():
    """Отказ товарной ручки — отказ всей карточки: без названия спрашивать
    каталог нечем, и «нет игры» отсюда не следует. Ветка своя: у `card` теперь
    два запроса, и первый ходит к другому хосту."""
    client = GogClient(SourceHttp("gog", transport=responding(500)))

    result = await client.card(WANTED, Kind.GAME)
    await client.aclose()

    assert isinstance(result, Refusal)
    assert result.reason is Reason.BROKEN


async def test_a_dead_network_on_the_product_endpoint_is_a_refusal():
    """`SourceHttp.get` отдаёт отказ вместо ответа — до этой ветки транспорт с
    готовым телом не доводит никогда."""
    client = GogClient(SourceHttp("gog", transport=unreachable()))

    result = await client.card(WANTED, Kind.GAME)
    await client.aclose()

    assert isinstance(result, Refusal)
    assert result.reason is Reason.NETWORK


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
    transport, seen = counting(responding(429, text="slow down"))

    client = GogClient(SourceHttp("gog", transport=transport))
    first = await client.search("Baldur's Gate", Kind.GAME)
    await client.search("Baldur's Gate", Kind.GAME)
    await client.aclose()

    assert isinstance(first, Refusal)
    assert first.reason is Reason.RATE
    assert len(seen) == 1, "второй запрос ушёл в сеть после 429"


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
    assert result.reason is Reason.BROKEN


async def test_the_catalog_is_asked_only_for_games_and_packs(fixture, gog_catalog):
    """Отсев дополнений делает сам запрос: у каталога есть `productType`.

    Наблюдается по выдаче, а не по объявлению константы, и выдача эта не
    подменяется готовой: иначе `in:game` вместо `in:game,pack` дал бы ту же
    выдачу, и потеря комплектов — «Fallout 2», «Ведьмак 3», — ради которых
    выбран второй, не наблюдалась бы ничем."""
    # Эмуляция сверяется с тем, что живой каталог ответил на самом деле, иначе
    # она проверяла бы наше представление о параметре, а не сам параметр.
    recorded = {one["title"]
                for one in fixture("gog/catalog_filtered.json")["products"]}
    client = GogClient(
        SourceHttp("gog", transport=httpx.MockTransport(gog_catalog)))

    result = await client.search("Baldur's Gate", Kind.GAME)
    await client.aclose()

    assert isinstance(result, Found)
    titles = {hit.title for hit in result.value}
    assert titles == recorded
    # Комплекты остаются: `Toolkit` у GOG — это `pack`.
    assert "Baldur's Gate 3 Toolkit" in titles
    assert not [one for one in titles if "Soundtrack" in one]


async def test_an_add_on_card_is_still_reachable_by_its_number(gog_catalog):
    """Отсев спрашивает только поиск. Путь вставленной ссылки двухшаговый —
    слаг в номер, номер в карточку, — и суженный вопрос на втором шаге отвечал
    бы «каталог не вернул этот номер», то есть отказом на существующий продукт.

    Сторож на `resolve_slug` этого не покрывает: он проверяет первый шаг."""
    def handler(request: httpx.Request) -> httpx.Response:
        if "api.gog.com/products" in str(request.url):
            return httpx.Response(
                200, json={"title": "Baldur's Gate: Siege of Dragonspear"})
        return gog_catalog(request)

    client = GogClient(SourceHttp("gog", transport=httpx.MockTransport(handler)))

    result = await client.card("1459335293", Kind.GAME)
    await client.aclose()

    assert isinstance(result, Found)
    assert result.value.item.source_id == "1459335293"
