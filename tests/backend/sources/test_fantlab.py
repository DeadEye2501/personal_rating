"""FantLab: запасная обложка книги, которой нет у Google.

Источник берётся ради одного — картинки, — и сверяется по двум признакам сразу.
Причина в том, что каждый по отдельности врёт: поиск у FantLab полнотекстовый и
на чужой ISBN отдаёт чужое издание, а ISBN у Google местами указывает не на ту
книгу. Оба замерены живьём 23.08.2026.

Тела ответов записаны, а не вписаны сюда: `scripts/record_fixtures.py`,
раздел `record_fantlab`.
"""

from contextlib import aclosing

import httpx

from backend.model import Found, Missing, Reason, Refusal
from backend.sources.fantlab.client import FantLabClient
from backend.sources.fantlab.parse import edition_of
from backend.sources.http import SourceHttp
from tests.conftest import counting, responding

# Номера, которыми записаны фикстуры. Названы здесь, чтобы спрошенное и
# записанное не разъезжались молча.
PICNIC_ISBN = "978-5-17-082983-5"
RINGS_ISBN = "978-5-271-46168-2"
RINGS_SECOND_ISBN = "978-985-18-1698-5"
FOREIGN_ISBN = "978-5-04-168446-4"
# Номер, которого нет ни в одной записанной строке: им проверяется, что сверка
# отводит. Это настоящий ISBN другого издания «Пикника».
OTHER_ISBN = "978-5-17-078696-1"
# Выдуманный по форме номер, которым записана фикстура «ничего не нашлось».
NOWHERE_ISBN = "978-5-00-000000-0"


def client(transport: httpx.MockTransport) -> FantLabClient:
    """Ключа FantLab не требует вовсе — как Steam, GOG и old-games.ru."""
    return FantLabClient(SourceHttp("fantlab", transport=transport))


def test_an_isbn_is_matched_with_dashes_and_without(fixture):
    """Номер пишут и так, и так — сверяются одни цифры.

    Сама сверка двух признаков стоит в двух соседних проверках: каждый признак
    по отдельности врёт, и держат правило они вдвоём."""
    payload = fixture("fantlab/search_exact_isbn.json")

    assert edition_of(payload, PICNIC_ISBN, "Пикник на обочине") == 118084
    assert edition_of(payload, "9785170829835", "Пикник на обочине") == 118084


def test_a_row_the_search_brought_by_itself_is_refused(fixture):
    """Поиск у FantLab полнотекстовый, а не по полю: замерено 23.08.2026 — на
    ISBN «Пикника» он вернул «Властелин Колец. Хранители Кольца», и разведка
    видела то же на четырёх строках из семнадцати.

    Записать такой промах фикстурой нельзя — вызвать его по своей воле нечем, —
    поэтому здесь проверяется сама сверка: строка «Властелина Колец» спрошена
    чужими для неё номером и названием и отвечать ими не должна."""
    rings = fixture("fantlab/search_by_isbn.json")

    assert edition_of(rings, OTHER_ISBN, "Пикник на обочине") is None


def test_another_printing_of_the_same_book_does_not_pass(fixture):
    """Вторая половина правила, и одна она держит весь ISBN: название у чужой
    строки чаще всего не сходится, а вот у **другого издания той же книги** оно
    сходится буква в букву. Издания разные — и обложки у них разные, так что
    подставить картинку соседнего значит показать человеку не ту книгу.

    Без этой проверки сверка ISBN не наблюдалась бы ничем: во всех остальных
    случаях чужую строку отводит название."""
    picnic = fixture("fantlab/search_exact_isbn.json")

    assert edition_of(picnic, OTHER_ISBN, "Пикник на обочине") is None


def test_a_foreign_isbn_of_google_does_not_pass_by_the_title(fixture):
    """Вторая половина той же защиты: ISBN у Google местами чужой —
    `9785041684464` числится за «Властелином Колец», а ведёт на «Снежный сон»
    Трониной. Название такую подмену ловит."""
    payload = fixture("fantlab/search_foreign_isbn.json")

    assert edition_of(payload, FOREIGN_ISBN, "Властелин Колец") is None


def test_an_edition_printed_in_two_countries_has_several_isbn(fixture):
    """«978-5-271-46168-2, 978-985-18-1698-5» — одно издание, два номера.
    Сверяется вхождение, а не строка целиком."""
    payload = fixture("fantlab/search_by_isbn.json")

    assert edition_of(payload, RINGS_SECOND_ISBN, "Властелин Колец") == 98039


def test_a_volume_of_a_cycle_matches_its_title(fixture):
    """У издания в названии бывает хвост тома, а у Google его нет: «Властелин
    Колец. Хранители Кольца» против «Властелин Колец». Совпадением считается
    общее начало."""
    payload = fixture("fantlab/search_by_isbn.json")

    assert edition_of(payload, RINGS_ISBN, "Властелин Колец") == 98039


def test_a_subtitle_of_google_matches_the_short_name_of_the_edition(fixture):
    """Обратная сторона того же правила: длиннее бывает и спрошенное — у Google
    к названию приклеен подзаголовок, а у издания его нет. Общее начало
    считается в обе стороны, иначе половина книг осталась бы без обложки."""
    payload = fixture("fantlab/search_exact_isbn.json")

    assert edition_of(payload, PICNIC_ISBN,
                      "Пикник на обочине: повесть") == 118084


def test_a_title_that_flattens_to_nothing_matches_nobody():
    """Пустое совпадает с чем угодно, и обе стороны от этого сторожатся.

    Проверка не теоретическая: приведение сводит к пустоте и непустое
    название — оно выбрасывает артикли и знаки. Сними её, и любое издание,
    найденное по номеру, стало бы обложкой такой книги.

    Тела рукописные: издание без названия у FantLab не выбрать по своей воле, а
    нужна здесь именно эта форма строки."""
    nameless = {"matches": [{"edition_id": "1", "isbn": PICNIC_ISBN,
                             "name": ""}]}
    named = {"matches": [{"edition_id": "2", "isbn": PICNIC_ISBN,
                          "name": "Пикник на обочине"}]}

    assert edition_of(nameless, PICNIC_ISBN, "Пикник на обочине") is None
    assert edition_of(named, PICNIC_ISBN, "The") is None


def test_nothing_to_look_for_without_an_isbn(fixture):
    """Без номера сверять нечем, и полнотекстовый поиск по одному названию
    привёл бы чужое издание."""
    payload = fixture("fantlab/search_exact_isbn.json")

    assert edition_of(payload, "", "Пикник на обочине") is None


async def test_the_cover_is_the_big_one_when_it_exists(fixture):
    """Крупная обложка — от 600×861 до 3129×4874, замерено разведкой."""
    async def handler(request: httpx.Request) -> httpx.Response:
        if "search-editions" in str(request.url):
            return httpx.Response(
                200, json=fixture("fantlab/search_exact_isbn.json"))
        return httpx.Response(200, headers={"content-type": "image/jpeg"})

    async with aclosing(client(httpx.MockTransport(handler))) as one:
        answer = await one.cover_for(PICNIC_ISBN, "Пикник на обочине")

    assert isinstance(answer, Found)
    assert answer.value == "https://fantlab.ru/images/editions/orig/118084"


async def test_the_picture_is_asked_without_downloading_it(fixture):
    """Наличие крупной картинки спрашивается `HEAD`-ом: у `orig` бывает 404 —
    три издания из тринадцати, — а качать ради проверки 350 КБ незачем.

    Способ запроса не наблюдается больше ничем: пошли клиент `GET`, и ответ был
    бы тот же самый, а трафик вырос бы в тысячи раз."""
    transport, seen = counting(responding(
        json=fixture("fantlab/search_exact_isbn.json"),
        headers={"content-type": "image/jpeg"}))

    async with aclosing(client(transport)) as one:
        await one.cover_for(PICNIC_ISBN, "Пикник на обочине")

    assert [(one.method, one.url.path) for one in seen] == [
        ("GET", "/search-editions"),
        ("HEAD", "/images/editions/orig/118084"),
    ]


async def test_a_missing_original_falls_back_to_the_small_one(fixture):
    """У трёх изданий из тринадцати крупной обложки нет вовсе — замерено. Тогда
    берётся маленькая: она есть всегда."""
    async def handler(request: httpx.Request) -> httpx.Response:
        if "search-editions" in str(request.url):
            return httpx.Response(
                200, json=fixture("fantlab/search_exact_isbn.json"))
        if "/orig/" in str(request.url):
            return httpx.Response(404, text="нет такой")
        return httpx.Response(200, headers={"content-type": "image/jpeg"})

    async with aclosing(client(httpx.MockTransport(handler))) as one:
        answer = await one.cover_for(PICNIC_ISBN, "Пикник на обочине")

    assert answer.value == "https://fantlab.ru/images/editions/big/118084"


async def test_a_stub_under_a_successful_code_is_not_a_cover(fixture):
    """Ловушка источника: адрес отвечает `200`, а отдаёт SVG-заглушку «обложки
    нет» в 56 КБ. По коду её не отличить, поэтому смотрится тип содержимого.

    Заглушка стоит только у крупной, а маленькая отвечает картинкой: отдавай
    обработчик SVG на оба адреса, и ответом был бы тот же запасной, что и при
    работающей проверке, — то есть она не наблюдалась бы вовсе."""
    async def handler(request: httpx.Request) -> httpx.Response:
        if "search-editions" in str(request.url):
            return httpx.Response(
                200, json=fixture("fantlab/search_exact_isbn.json"))
        if "/orig/" in str(request.url):
            return httpx.Response(200,
                                  headers={"content-type": "image/svg+xml"})
        return httpx.Response(200, headers={"content-type": "image/jpeg"})

    async with aclosing(client(httpx.MockTransport(handler))) as one:
        answer = await one.cover_for(PICNIC_ISBN, "Пикник на обочине")

    assert answer.value == "https://fantlab.ru/images/editions/big/118084"


async def test_a_picture_type_under_a_broken_code_is_not_a_cover(fixture):
    """Тип содержимого смотрится вместе с кодом, а не вместо него: прокси
    отвечает своим кодом, оставляя заголовок прежним, и картинкой такой ответ
    быть перестал."""
    async def handler(request: httpx.Request) -> httpx.Response:
        if "search-editions" in str(request.url):
            return httpx.Response(
                200, json=fixture("fantlab/search_exact_isbn.json"))
        if "/orig/" in str(request.url):
            return httpx.Response(500, headers={"content-type": "image/jpeg"})
        return httpx.Response(200, headers={"content-type": "image/jpeg"})

    async with aclosing(client(httpx.MockTransport(handler))) as one:
        answer = await one.cover_for(PICNIC_ISBN, "Пикник на обочине")

    assert answer.value == "https://fantlab.ru/images/editions/big/118084"


async def test_the_search_asks_by_the_isbn_it_was_given(fixture):
    """Адрес и доводы запроса — то, чего не сторожит ни один разбор: подмени
    путь, и все проверки разбора останутся зелёными, а живой поиск замолчит.

    Страница спрашивается первая: со второй приехала бы чужая половина выдачи
    либо пустота, и книга осталась бы без обложки молча."""
    transport, seen = counting(
        responding(json=fixture("fantlab/search_exact_isbn.json")))

    async with aclosing(client(transport)) as one:
        await one.cover_for(PICNIC_ISBN, "Пикник на обочине")

    assert str(seen[0].url).startswith("https://api.fantlab.ru/search-editions")
    assert seen[0].url.params.get("q") == PICNIC_ISBN
    assert seen[0].url.params.get("page") == "1"


async def test_a_book_the_source_does_not_know_is_an_absence(fixture):
    """Каталог FantLab — фантастика и смежное; обычной прозы там нет вовсе, и
    это не отказ, а «такого у меня нет».

    Записанный ответ показывает, чем это выглядит на самом деле: пустого
    `matches` источник не отдаёт вовсе — на несуществующий номер приезжают
    девять чужих изданий, и у восьми из них номера нет совсем. Отводит их
    сверка."""
    async with aclosing(client(responding(
            json=fixture("fantlab/search_nothing.json")))) as one:
        answer = await one.cover_for(NOWHERE_ISBN, "Бухгалтерский учёт")

    assert isinstance(answer, Missing)


async def test_a_refusal_of_the_source_is_not_an_absence():
    """Отказ и отсутствие путать нельзя: отрицательный факт живёт в базе неделю,
    а «источник молчит» лечится повтором."""
    async with aclosing(client(responding(500, text="сломалось"))) as one:
        answer = await one.cover_for("9785170829835", "Пикник на обочине")

    assert isinstance(answer, Refusal)
    assert answer.reason is Reason.BROKEN


async def test_a_row_without_an_isbn_asks_nobody(fixture):
    """У сканов и журналов ISBN нет вовсе — спрашивать нечем."""
    transport, seen = counting(
        responding(json=fixture("fantlab/search_exact_isbn.json")))

    async with aclosing(client(transport)) as one:
        answer = await one.cover_for("", "Книжная летопись")

    assert isinstance(answer, Missing)
    assert seen == [], "без номера запроса быть не должно"
