"""FantLab: запасная обложка книги, которой нет у Google.

Источник берётся ради одного — картинки, — и сверяется по двум признакам сразу.
Причина в том, что каждый по отдельности врёт: поиск у FantLab полнотекстовый и
на чужой ISBN отдаёт чужое издание, а ISBN у Google местами указывает не на ту
книгу. Оба замерены живьём 23.08.2026.
"""

from contextlib import aclosing

import httpx

from backend.model import Found, Missing, Reason, Refusal
from backend.sources.fantlab.client import FantLabClient
from backend.sources.fantlab.parse import edition_of
from backend.sources.http import SourceHttp
from tests.conftest import counting, responding

PICNIC = {"matches": [{"edition_id": "118084", "isbn": "978-5-17-082983-5",
                       "name": "Пикник на обочине", "year": 2014}],
          "total_found": 1}


def client(transport: httpx.MockTransport) -> FantLabClient:
    """Ключа FantLab не требует вовсе — как Steam, GOG и old-games.ru."""
    return FantLabClient(SourceHttp("fantlab", transport=transport))


def test_an_edition_needs_both_the_isbn_and_the_title():
    """Оба признака, а не один: сойдясь вместе, они друг друга страхуют."""
    assert edition_of(PICNIC, "978-5-17-082983-5", "Пикник на обочине") == 118084
    assert edition_of(PICNIC, "9785170829835", "Пикник на обочине") == 118084


def test_a_row_the_search_brought_by_itself_is_refused():
    """Замерено 23.08.2026: на ISBN «Пикника» FantLab вернул «Властелин Колец.
    Хранители Кольца» — поиск у него полнотекстовый, а не по полю."""
    stranger = {"matches": [{"edition_id": "98039",
                             "isbn": "978-5-271-46168-2",
                             "name": "Властелин Колец. Хранители Кольца"}]}

    assert edition_of(stranger, "978-5-17-078696-1", "Пикник на обочине") is None


def test_a_foreign_isbn_of_google_does_not_pass_by_the_title():
    """Вторая половина той же защиты: ISBN у Google местами чужой —
    `9785041684464` числится за «Властелином Колец», а ведёт на «Снежный сон»
    Трониной. Название такую подмену ловит."""
    payload = {"matches": [{"edition_id": "1", "isbn": "9785041684464",
                            "name": "Снежный сон"}]}

    assert edition_of(payload, "9785041684464", "Властелин Колец") is None


def test_an_edition_printed_in_two_countries_has_several_isbn():
    """«978-5-271-46168-2, 978-985-16-9724-1» — одно издание, два номера.
    Сверяется вхождение, а не строка целиком."""
    payload = {"matches": [{"edition_id": "98039",
                            "isbn": "978-5-271-46168-2, 978-985-16-9724-1",
                            "name": "Властелин Колец"}]}

    assert edition_of(payload, "9789851697241", "Властелин Колец") == 98039


def test_a_volume_of_a_cycle_matches_its_title():
    """У издания в названии бывает хвост тома, а у Google его нет: «Властелин
    Колец. Хранители Кольца» против «Властелин Колец». Совпадением считается
    общее начало."""
    payload = {"matches": [{"edition_id": "98039", "isbn": "9785271461682",
                            "name": "Властелин Колец. Хранители Кольца"}]}

    assert edition_of(payload, "9785271461682", "Властелин Колец") == 98039


def test_nothing_to_look_for_without_an_isbn():
    """Без номера сверять нечем, и полнотекстовый поиск по одному названию
    привёл бы чужое издание."""
    assert edition_of(PICNIC, "", "Пикник на обочине") is None


async def test_the_cover_is_the_big_one_when_it_exists():
    """Крупная обложка — от 600×861 до 3129×4874, замерено разведкой."""
    async def handler(request: httpx.Request) -> httpx.Response:
        if "search-editions" in str(request.url):
            return httpx.Response(200, json=PICNIC)
        return httpx.Response(200, headers={"content-type": "image/jpeg"})

    async with aclosing(client(httpx.MockTransport(handler))) as one:
        answer = await one.cover_for("978-5-17-082983-5", "Пикник на обочине")

    assert isinstance(answer, Found)
    assert answer.value == "https://fantlab.ru/images/editions/orig/118084"


async def test_a_missing_original_falls_back_to_the_small_one():
    """У трёх изданий из тринадцати крупной обложки нет вовсе — замерено. Тогда
    берётся маленькая: она есть всегда."""
    async def handler(request: httpx.Request) -> httpx.Response:
        if "search-editions" in str(request.url):
            return httpx.Response(200, json=PICNIC)
        if "/orig/" in str(request.url):
            return httpx.Response(404, text="нет такой")
        return httpx.Response(200, headers={"content-type": "image/jpeg"})

    async with aclosing(client(httpx.MockTransport(handler))) as one:
        answer = await one.cover_for("978-5-17-082983-5", "Пикник на обочине")

    assert answer.value == "https://fantlab.ru/images/editions/big/118084"


async def test_a_stub_under_a_successful_code_is_not_a_cover():
    """Ловушка источника: адрес отвечает `200`, а отдаёт SVG-заглушку «обложки
    нет» в 56 КБ. По коду её не отличить, поэтому смотрится тип содержимого."""
    async def handler(request: httpx.Request) -> httpx.Response:
        if "search-editions" in str(request.url):
            return httpx.Response(200, json=PICNIC)
        return httpx.Response(200, headers={"content-type": "image/svg+xml"})

    async with aclosing(client(httpx.MockTransport(handler))) as one:
        answer = await one.cover_for("978-5-17-082983-5", "Пикник на обочине")

    assert answer.value == "https://fantlab.ru/images/editions/big/118084"


async def test_the_search_asks_by_the_isbn_it_was_given():
    """Адрес и довод запроса — то, чего не сторожит ни один разбор: подмени
    путь, и все проверки разбора останутся зелёными, а живой поиск замолчит."""
    transport, seen = counting(responding(json=PICNIC))

    async with aclosing(client(transport)) as one:
        await one.cover_for("978-5-17-082983-5", "Пикник на обочине")

    assert str(seen[0].url).startswith("https://api.fantlab.ru/search-editions")
    assert "q=978-5-17-082983-5" in str(seen[0].url)


async def test_a_book_the_source_does_not_know_is_an_absence():
    """Каталог FantLab — фантастика и смежное; обычной прозы там нет вовсе, и
    это не отказ, а «такого у меня нет»."""
    async with aclosing(client(responding(json={"matches": [], "total_found": 0}))) as one:
        answer = await one.cover_for("9785041684464", "Бухгалтерский учёт")

    assert isinstance(answer, Missing)


async def test_a_refusal_of_the_source_is_not_an_absence():
    """Отказ и отсутствие путать нельзя: отрицательный факт живёт в базе неделю,
    а «источник молчит» лечится повтором."""
    async with aclosing(client(responding(500, text="сломалось"))) as one:
        answer = await one.cover_for("9785170829835", "Пикник на обочине")

    assert isinstance(answer, Refusal)
    assert answer.reason is Reason.BROKEN


async def test_a_row_without_an_isbn_asks_nobody():
    """У сканов и журналов ISBN нет вовсе — спрашивать нечем."""
    transport, seen = counting(responding(json=PICNIC))

    async with aclosing(client(transport)) as one:
        answer = await one.cover_for("", "Книжная летопись")

    assert isinstance(answer, Missing)
    assert seen == [], "без номера запроса быть не должно"
