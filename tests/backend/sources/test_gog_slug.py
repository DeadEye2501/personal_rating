"""Слаг из адреса GOG в номер каталога."""

import httpx

from backend.sources.errors import Found, Missing, Reason, Refusal
from backend.sources.gog.client import GogClient
from backend.sources.gog.parse import find_slug
from backend.sources.http import SourceHttp

SLUG = "arcanum_of_steamworks_and_magick_obscura"


def client(handler) -> GogClient:
    return GogClient(SourceHttp("gog", transport=httpx.MockTransport(handler)))


def test_an_exact_slug_gives_the_number(fixture):
    assert find_slug(fixture("gog/catalog_by_slug.json"), SLUG) == "1207658930"


def test_a_prefix_of_a_real_slug_is_not_enough(fixture):
    """Поиск GOG никогда не говорит «не найдено»: на бессмыслицу приходит 22
    несвязанные игры. Совпадение должно быть строгим — при нестрогом «arcanum»
    привязал бы к себе и саундтрек, и саму игру, какая попадётся первой."""
    assert find_slug(fixture("gog/catalog_by_slug.json"), "arcanum") is None


def test_the_exact_neighbour_is_told_apart(fixture):
    """Два продукта с общим началом слага — берётся тот, что назван."""
    assert find_slug(
        fixture("gog/catalog_by_slug.json"), "arcanum_soundtrack"
    ) == "1207659111"


def test_a_numeric_identifier_comes_back_as_a_string():
    """Номер уезжает в `source_id`, а это текстовая колонка: в фикстуре он
    строкой, но живьём форма поля не проверена, и числом он приехать может."""
    assert find_slug({"products": [{"id": 1207658930, "slug": SLUG}]},
                     SLUG) == "1207658930"


def test_two_products_with_one_slug_give_the_first():
    """Слаг — это адрес, и двух одинаковых у GOG быть не должно. Случись такое,
    берём первый: порядок в ответе задаёт каталог, и выбирать между двумя нам
    нечем — лишь бы выбор не зависел от прогона."""
    assert find_slug({"products": [
        {"id": "1", "slug": SLUG},
        {"id": "2", "slug": SLUG},
    ]}, SLUG) == "1"


def test_an_empty_answer_gives_nothing():
    assert find_slug({"products": []}, SLUG) is None


def test_an_answer_without_products_gives_nothing():
    assert find_slug({}, SLUG) is None


async def test_the_number_comes_back(fixture):
    result = await client(
        lambda request: httpx.Response(
            200, json=fixture("gog/catalog_by_slug.json")
        )
    ).resolve_slug(SLUG)

    assert isinstance(result, Found)
    assert result.value == "1207658930"


async def test_the_slug_becomes_words_in_the_query(fixture):
    """Форма запроса — самое хрупкое место задачи: живьём она не проверена. Хотя
    бы зафиксируем, что уходит именно то, что задумано."""
    asked = []

    def handler(request: httpx.Request) -> httpx.Response:
        # Сверяем разобранный параметр, а не строку адреса: как httpx кодирует
        # пробел, к делу не относится.
        asked.append(request.url.params["query"])
        return httpx.Response(200, json=fixture("gog/catalog_by_slug.json"))

    await client(handler).resolve_slug(SLUG)

    assert asked == ["like:arcanum of steamworks and magick obscura"]


async def test_a_slug_the_catalog_does_not_have_is_missing():
    result = await client(
        lambda request: httpx.Response(200, json={"products": []})
    ).resolve_slug(SLUG)

    assert isinstance(result, Missing)


async def test_a_broken_answer_is_a_refusal():
    result = await client(
        lambda request: httpx.Response(200, content="не JSON".encode())
    ).resolve_slug(SLUG)

    assert isinstance(result, Refusal)
    assert result.reason is Reason.BROKEN


async def test_a_server_error_is_a_refusal():
    result = await client(lambda request: httpx.Response(500)).resolve_slug(SLUG)

    assert isinstance(result, Refusal)


async def test_a_dead_network_is_a_refusal():
    """`SourceHttp.get` отдаёт отказ вместо ответа — ветка, до которой
    `MockTransport` с готовым телом не доводит никогда."""

    def dead(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("сети нет", request=request)

    result = await client(dead).resolve_slug(SLUG)

    assert isinstance(result, Refusal)
    assert result.reason is Reason.NETWORK
