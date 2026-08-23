"""Google Books: седьмой источник и единственный, откуда приходят книги.

Главная его ловушка замерена живьём 22.08.2026: `503` — это «занят сейчас», а
не «не нашёл». Прогон без повтора нашёл 5 книг из 10, с повтором — 8, и все пять
потерь были занятостью. Считать её пустой выдачей значит терять половину
каталога при зелёном наборе."""

from datetime import timedelta

from contextlib import aclosing

import httpx

from backend.model import (
    IdSource,
    SEARCH_SIZE,
    CompanyRole,
    Found,
    GenreSource,
    Kind,
    Missing,
    PersonRole,
    Reason,
    Refusal,
    Source,
)
from backend.sources.backoff import until_midnight
from backend.sources.busy import ATTEMPTS
from backend.sources.google_books.client import GoogleBooksClient
from backend.sources.google_books.parse import (
    covers,
    parse_by_author,
    parse_card,
    parse_search,
)
from backend.sources.http import SourceHttp
from tests.conftest import FakeClock, counting, responding

KEY = "ключ-google-books"


def client(transport: httpx.MockTransport) -> GoogleBooksClient:
    """Клиент на заданном транспорте. Ключ непустой: с пустым Google отвечает
    отказом по квоте, и такой клиент проверял бы не то."""
    return GoogleBooksClient(SourceHttp("google_books", transport=transport),
                              (KEY,))


async def searched(transport: httpx.MockTransport, query: str = "дюна"):
    async with aclosing(client(transport)) as one:
        return await one.search(query, Kind.BOOK)


async def carded(transport: httpx.MockTransport, source_id: str = "-u8-DwAAQBAJ"):
    async with aclosing(client(transport)) as one:
        return await one.card(source_id, Kind.BOOK)


def test_the_search_gives_a_row_for_every_volume(fixture):
    """Строк ровно столько, сколько томов в `items`: обрезанная выдача выглядела
    бы как бедный каталог, а не как поломка разбора."""
    payload = fixture("google_books/search_dune.json")

    hits = parse_search(payload)

    assert len(hits) == len(payload["items"])
    assert len(hits) > 1, "фикстура с одной строкой ничего не сторожит"


def test_a_search_row_carries_what_the_volume_shows(fixture):
    """Название, номер тома и год — из строки выдачи. Тип и источник ставит
    разбор: перепутай их, и книга уехала бы в чужую вкладку."""
    hits = parse_search(fixture("google_books/search_dune.json"))

    first = hits[0]
    assert (first.kind, first.source) == (Kind.BOOK, Source.GOOGLE_BOOKS)
    assert first.source_id == "4kbYExSCa6oC"
    assert first.title == "The Science of Dune"
    assert first.year == 2007


def test_a_volume_without_a_cover_still_becomes_a_row():
    """Обложки нет у части книг, и строка без неё обязана остаться в выдаче —
    иначе кусок каталога исчезает молча."""
    without = {"items": [{"id": "x", "volumeInfo": {"title": "Без обложки"}}]}

    assert parse_search(without)[0].poster_url == ""


def test_a_row_takes_the_only_level_the_search_gives(fixture):
    """Выдача обрезает путь BISAC до верхушки — замерено: у «Задачи трёх тел»
    там `Fiction`, а полный путь отдаёт только карточка. Верхний уровень
    справочник знает (`Fiction` — это `Проза`), и терять его незачем: без метки
    строка выдачи стоит без жанра вовсе."""
    hits = parse_search(fixture("google_books/search_dune.json"))

    first = hits[0]
    assert first.genre_ext_ids == ((GenreSource.GOOGLE_BOOKS, "Social Science"),)


def test_the_genre_comes_from_the_second_level_of_the_path(fixture):
    """Спека требует второй уровень BISAC: первый — `Fiction` — покрывает треть
    всех книг, третий дробен до `Space Exploration`. Наблюдается меткой,
    уехавшей в `genre_ext_ids`, а не разбором строки: справочник сверяет
    именно её."""
    card = parse_card(fixture("google_books/volume_three_body.json"))

    assert (GenreSource.GOOGLE_BOOKS, "Science Fiction") in card.genre_ext_ids
    assert (GenreSource.GOOGLE_BOOKS, "Fiction") not in card.genre_ext_ids


def test_four_paths_of_one_book_give_one_genre(fixture):
    """У «Задачи трёх тел» четыре пути BISAC, и второй уровень у всех четырёх
    один и тот же. Не сними повтор — и книга получит четыре одинаковых жанра:
    в карточке они встанут в ряд четырьмя одинаковыми метками."""
    payload = fixture("google_books/volume_three_body.json")

    card = parse_card(payload)

    assert len(payload["volumeInfo"]["categories"]) == 4
    assert card.genre_ext_ids == ((GenreSource.GOOGLE_BOOKS, "Science Fiction"),)


def test_a_general_second_level_falls_back_to_the_first():
    """`Fiction / General` — это «художественная, и больше Google не сказал».
    Второй уровень тут пустышка, и жанром обязан стать первый."""
    payload = {"id": "x",
               "volumeInfo": {"title": "Т", "categories": ["Fiction / General"]}}

    assert parse_card(payload).genre_ext_ids == (
        (GenreSource.GOOGLE_BOOKS, "Fiction"),)


def test_a_volume_without_categories_gets_no_genre(fixture):
    """У части книг `categories` нет вовсе — замерено, у `Sapiens`. Пустая
    метка уехала бы в справочник и не совпала бы ни с одним правилом, зато
    заняла бы строку в базе."""
    card = parse_card(fixture("google_books/volume_no_cover.json"))

    assert card.genre_ext_ids == ()


def test_the_author_is_a_person_and_the_publisher_is_a_company(fixture):
    """Роли не должны разъехаться: автор идёт туда же, где режиссёр, а
    издательство — туда, где студия. Перепутанные местами роли — тот самый
    дефект, который однажды прошёл шесть мутаций молча."""
    card = parse_card(fixture("google_books/volume_three_body.json"))

    assert [one.name for one in card.people] == ["Лю Цысинь"]
    assert [one.role for one in card.people] == [PersonRole.AUTHOR]
    assert [one.name for one in card.companies] == ["Эксмо"]
    assert [one.role for one in card.companies] == [CompanyRole.PUBLISHER]


def test_an_author_comes_without_any_identity(fixture):
    """У Google `authors` — голые строки, идентичности автора нет вовсе.
    Выдуманный суррогат склеил бы двух разных Ивановых в одну строку навсегда:
    таких склеивают по имени, как студии магазинов."""
    card = parse_card(fixture("google_books/volume_three_body.json"))

    assert card.people[0].source is None
    assert card.people[0].source_id is None


def test_a_volume_without_authors_still_becomes_a_card(fixture):
    """У сборников и трудов конференций автора нет — замерено. Карточка обязана
    собраться: иначе такая книга не заводится вовсе, а издательство у неё есть."""
    card = parse_card(fixture("google_books/volume_no_author.json"))

    assert card.people == ()
    assert card.companies


def test_the_rating_never_reaches_the_card(fixture):
    """Замер: оценка есть у четырёх томов из двенадцати, и у всех четырёх от
    одного до четырёх голосов при значениях 5, 5, 5 и 4. Рядом с «IMDb 8.4»
    такая пятёрка читалась бы как мнение публики и врала бы."""
    payload = fixture("google_books/volume_three_body.json")

    assert payload["volumeInfo"]["averageRating"], "фикстура без оценки не сторожит"
    assert parse_card(payload).ratings == ()


def test_a_card_carries_the_title_year_and_synopsis(fixture):
    """Три поля, ради которых карточка и запрашивается вторым запросом: в
    выдаче года и синопсиса может не быть вовсе, а в базу они уезжают
    навсегда."""
    card = parse_card(fixture("google_books/volume_three_body.json"))

    assert card.item.kind is Kind.BOOK
    assert card.item.source_id == "-u8-DwAAQBAJ"
    assert card.item.title == "Задача трех тел"
    assert card.item.year == 2017
    assert "Они придут" in card.item.synopsis


def test_the_synopsis_comes_without_markup(fixture):
    """Замерено: у «Задачи трёх тел» описание приходит абзацами HTML — весь
    текст обёрнут в `<p>`. Страница показывает синопсис текстом и экранирует
    его, так что теги приехали бы человеку дословно и уехали бы в базу
    навсегда: перезапрос карточки идёт раз в месяц."""
    payload = fixture("google_books/volume_three_body.json")

    card = parse_card(payload)

    assert "<p>" in payload["volumeInfo"]["description"], "фикстура без разметки"
    assert "<" not in card.item.synopsis
    assert card.item.synopsis.startswith("Они придут")


def test_the_cover_of_a_publisher_volume_takes_the_step_nearest_our_size():
    """У издательского тома верна любая ступень — замерено 23.08.2026 на семи
    таких томах, — и берётся ближайшая к нашей мерке 500×750 сверху: `medium`
    575×812. Самая крупная не берётся нарочно: обрезка ужимает до 500×750 и не
    растягивает, так что `extraLarge` 2448×3116 дал бы тот же итог за впятеро
    больший вес."""
    publisher = "http://books.google.com/books/publisher/content?id=1"
    payload = {"id": "1", "volumeInfo": {"title": "Дюна", "imageLinks": {
        "smallThumbnail": f"{publisher}&zoom=5",
        "thumbnail": f"{publisher}&zoom=1",
        "small": f"{publisher}&w=300",
        "medium": f"{publisher}&w=575",
        "large": f"{publisher}&w=800",
        "extraLarge": f"{publisher}&w=1800",
    }}}

    assert parse_card(payload).item.poster_url == f"{publisher}&w=575"


def test_the_cover_of_a_scan_takes_the_thumbnail_and_no_bigger():
    """У сканированного тома крупные ступени бывают полосой страницы: 300×48,
    575×92, 800×128 при пропорции 6.25 — замерено 23.08.2026 на трёх сканах из
    пяти. `thumbnail` при этом обложка у всех до единого, и берётся он.

    Отличает скан сам адрес: `/books/content` против
    `/books/publisher/content` у издательского."""
    scan = "http://books.google.com/books/content?id=1"
    payload = {"id": "1", "volumeInfo": {"title": "Скан", "imageLinks": {
        "thumbnail": f"{scan}&zoom=1",
        "medium": f"{scan}&zoom=3",
        "extraLarge": f"{scan}&zoom=6",
    }}}

    assert parse_card(payload).item.poster_url == f"{scan}&zoom=1"


def test_the_cover_falls_back_to_what_is_there():
    """Ступеней у тома бывает две: в строке выдачи Google объявляет только
    `thumbnail` и `smallThumbnail`, а у сканированных томов и в карточке нет ни
    одной. Замерено 23.08.2026 на живых данных."""
    thumbnail = {"id": "1", "volumeInfo": {
        "title": "Дюна", "imageLinks": {"thumbnail": "http://g/t?zoom=1"}}}
    without = {"id": "2", "volumeInfo": {"title": "Скан"}}

    hits = parse_search({"items": [thumbnail, without]})

    assert [hit.poster_url for hit in hits] == ["http://g/t?zoom=1", ""]


def test_the_cover_of_a_volume_is_not_rebuilt_by_hand(fixture):
    """Адрес уезжает как есть: у части томов в хвосте стоит токен `imgtk`, без
    которого картинка не отдаётся."""
    payload = fixture("google_books/volume_three_body.json")

    card = parse_card(payload)

    assert card.item.poster_url in payload["volumeInfo"]["imageLinks"].values()
    assert "zoom=3" not in card.item.poster_url


async def test_the_search_asks_google_with_the_query_and_the_key(fixture):
    """Адрес и доводы запроса — то, чего не сторожит ни один разбор: подмени
    путь, и все проверки разбора останутся зелёными, а живой поиск замолчит.
    Этим дефектом GOG был сломан целиком при 905 зелёных тестах.

    Порция названа явно: по умолчанию Google отдаёт десять строк — вдвое меньше,
    чем показывает выдача поиска."""
    transport, asked = counting(
        responding(json=fixture("google_books/search_dune.json")))

    await searched(transport, "дюна")

    url = asked[0].url
    assert url.path == "/books/v1/volumes"
    assert url.params.get("q") == "дюна"
    assert url.params.get("key") == KEY
    assert url.params.get("maxResults") == str(SEARCH_SIZE)


async def test_the_second_portion_is_asked_from_the_shift(fixture):
    """Смещение обязано доехать до самого запроса, а не только до сервиса.
    Замени `startIndex` константой — и лента догружала бы одну и ту же первую
    двадцатку без конца, списывая запросы из тысячи суточных, а прокрутка
    выглядела бы застрявшей.

    У Google `startIndex` — это смещение буквально, без перевода в страницы;
    вторая порция записана слайсом 1 ровно под эту проверку."""
    transport, asked = counting(
        responding(json=fixture("google_books/search_dune_page2.json")))

    answer = await client(transport).search("дюна", Kind.BOOK, SEARCH_SIZE)

    assert isinstance(answer, Found) and answer.value
    assert asked[0].url.params.get("startIndex") == str(SEARCH_SIZE)


async def test_the_first_portion_starts_at_the_beginning(fixture):
    """Обратная половина: без смещения выдача начинается с нуля. Без неё
    «доехало» неотличимо от «уехало всегда», а вечное `startIndex=20`
    выбрасывало бы первые двадцать книг из каждой выдачи."""
    transport, asked = counting(
        responding(json=fixture("google_books/search_dune.json")))

    await client(transport).search("дюна", Kind.BOOK)

    assert asked[0].url.params.get("startIndex") == "0"


async def test_the_card_is_asked_by_the_volume_identifier(fixture):
    """Том берётся своей ручкой, а не поиском по номеру: полный путь BISAC есть
    только у неё — замерено, выдача отдаёт `Fiction`, карточка того же тома —
    `Fiction / Science Fiction / Hard Science Fiction`."""
    transport, asked = counting(
        responding(json=fixture("google_books/volume_three_body.json")))

    await carded(transport, "-u8-DwAAQBAJ")

    assert asked[0].url.path == "/books/v1/volumes/-u8-DwAAQBAJ"
    assert asked[0].url.params.get("key") == KEY


async def test_the_books_of_an_author_come_by_name(fixture):
    """У Google идентичности автора нет вовсе: `authors` — голые строки.
    Спрашивается он оператором `inauthor:`, и тёзки с разночтениями приезжают
    вместе — замерено, по «Frank Herbert» в двадцати строках стоят и
    `FRANK. HERBERT`, и `Brian Herbert`. Это цена, а не поломка.

    Наблюдается спрошенным доводом, а не выдачей: выдача у поиска по названию и
    у поиска по автору одинакова, а запрос — нет."""
    transport, asked = counting(
        responding(json=fixture("google_books/inauthor_herbert.json")))

    answer = await client(transport).credits_of("Frank Herbert", Kind.BOOK)

    assert isinstance(answer, Found) and answer.value
    assert asked[0].url.params.get("q") == 'inauthor:"Frank Herbert"'


async def test_the_identity_of_an_author_is_his_name(fixture):
    """Своей ручки людей у Google нет, и притворяться, что есть, клиент не
    будет: найденный «человек» — это само набранное имя, и с ним же придут
    спрашивать книги. Строка ровно одна: отбирать среди авторов нечего."""
    transport, asked = counting(responding(json={}))

    answer = await client(transport).find_people("Фрэнк Герберт")

    assert isinstance(answer, Found)
    assert [one.source_id for one in answer.value] == ["Фрэнк Герберт"]
    assert asked == [], "у Google нет ручки людей — спрашивать было нечего"


async def test_a_busy_answer_is_retried_and_not_taken_for_emptiness(replay):
    """Главная ловушка источника, замерена живьём: первый прогон дал 5 книг из
    10 и был неверен — пять «не найдено» оказались `503`. Считать это пустой
    выдачей значит терять половину книг при зелёном наборе."""
    transport, asked = counting(replay("google_books/busy.json",
                                       "google_books/search_dune.json"))

    answer = await searched(transport)

    assert isinstance(answer, Found) and answer.value
    assert len(asked) == 2, "занятость обязана быть перепрошена, а не принята"


async def test_a_busy_source_is_not_shut_off_by_the_breaker(replay):
    """`503` — штатный ответ занятого Google, и утечь в предохранитель он не
    должен: иначе после каждого поиска источник замолкал бы на пятнадцать
    секунд, а выглядело бы это как «Google работает через раз».

    Наблюдается тремя следствиями сразу: клиент сдаётся отказом по частоте,
    предохранитель после этого закрыт, и следующий вопрос источник отвечает
    выдачей — то есть замолчал он ровно на один запрос, а не на срок."""
    busy = ["google_books/busy.json"] * ATTEMPTS
    http = SourceHttp("google_books",
                      transport=replay(*busy, "google_books/search_dune.json"))
    one = GoogleBooksClient(http, (KEY,))

    given_up = await one.search("дюна", Kind.BOOK)
    again = await one.search("дюна", Kind.BOOK)
    await one.aclose()

    assert isinstance(given_up, Refusal) and given_up.reason is Reason.RATE
    assert not http.breaker.is_open(), "предохранитель взведён штатным 503"
    assert isinstance(again, Found), "источник замолчал после занятости"


async def test_the_quota_trips_the_breaker(replay):
    """Взведённый предохранитель — не украшение: без него каждая карточка
    прокрутки идёт в исчерпанную квоту и досиживает свой таймаут.

    Срок именно до полуночи, и он назван числом: квота у Google суточная,
    `Retry-After` он не шлёт, а любая своя константа в часах молчала бы —
    отказ приходил бы тот же самый, просто раньше, и потраченный запрос никто
    не вернул бы. Часы остановлены, иначе сравнивать не с чем."""
    clock = FakeClock()
    http = SourceHttp("google_books", clock=clock,
                      transport=replay("google_books/quota.json"))

    answer = await GoogleBooksClient(http, (KEY,)).search("дюна", Kind.BOOK)

    assert isinstance(answer, Refusal) and answer.reason is Reason.QUOTA
    assert answer.retry_after == until_midnight(clock())
    assert http.breaker.is_open()

    # Следствие срока, а не его пересказ: за минуту до полуночи источник ещё
    # молчит, а после неё отвечает снова.
    clock.advance(until_midnight(clock()) - timedelta(minutes=1))
    assert http.breaker.is_open()
    clock.advance(timedelta(minutes=1))
    assert not http.breaker.is_open()


async def test_the_spare_key_takes_over_when_the_quota_runs_out():
    """Суточная квота считается на проект, и ключ от другого аккаунта
    продлевает день. Решение пользователя 23.08.2026.

    Наблюдается ключом на проводе, а не тем, что ответ приехал: подставь клиент
    первый ключ второй раз — выдача была бы та же самая, и подмена прошла бы
    молча."""
    keys = []

    def handler(request: httpx.Request) -> httpx.Response:
        keys.append(request.url.params.get("key"))
        if request.url.params.get("key") == "кончился":
            return httpx.Response(429, json={"error": {"code": 429}})
        return httpx.Response(200, json={"items": []})

    http = SourceHttp("google_books", transport=httpx.MockTransport(handler))
    client = GoogleBooksClient(http, ("кончился", "запасной"))

    first = await client.search("дюна", Kind.BOOK)
    second = await client.search("герберт", Kind.BOOK)

    assert isinstance(first, Found), "запасной ключ не подставился"
    assert isinstance(second, Found)
    assert not http.breaker.is_open(), "источник закрыт, хотя ключ ещё есть"
    # Исчерпанный ключ спрашивают один раз: возвращаться к нему до полуночи
    # значит тратить по походу в сеть на каждом запросе.
    assert keys == ["кончился", "запасной", "запасной"]


async def test_the_last_key_out_of_quota_closes_the_source():
    """Запасной ключ отодвигает отказ, но не отменяет его: кончились все —
    источник закрывается до полуночи, как закрывался с одним ключом.

    Без этого предохранитель не взводился бы вовсе, и каждая карточка
    прокрутки шла бы в исчерпанную квоту досиживать свой таймаут."""
    http = SourceHttp("google_books",
                      transport=responding(429, json={"error": {"code": 429}}))

    answer = await GoogleBooksClient(http, ("первый", "второй")).search(
        "дюна", Kind.BOOK)

    assert isinstance(answer, Refusal) and answer.reason is Reason.QUOTA
    assert http.breaker.is_open()


async def test_a_bad_key_is_not_a_quota(replay):
    """Замерено: без ключа Google отвечает `429`, с негодным — `400`. Смешай их,
    и негодный ключ закрыл бы источник до полуночи, а человек увидел бы
    «кончилась квота» там, где надо вписать другой ключ."""
    http = SourceHttp("google_books", transport=replay("google_books/bad_key.json"))

    answer = await GoogleBooksClient(http, ("не-ключ",)).search("дюна", Kind.BOOK)

    assert isinstance(answer, Refusal) and answer.reason is Reason.KEY
    assert not http.breaker.is_open(), "битый ключ сроком не лечится"


async def test_an_unknown_volume_is_missing_and_not_a_refusal(replay):
    """`404` с разобранным телом — это «такого тома у меня нет», и записать это
    можно: отрицательный факт живёт неделю. Отличается от занятости кодом —
    замерено, негодный по форме номер даёт `503`."""
    assert isinstance(await carded(replay("google_books/absent.json")), Missing)


async def test_a_page_under_a_four_hundred_and_four_is_not_an_answer():
    """Чужой периметр отдаёт свой `404` текстом, и поверить ему значит поселить
    в базе ложь на неделю. Правило проекта общее, и седьмой источник его не
    отменяет."""
    answer = await carded(responding(404, text="<html>Not found</html>"))

    assert isinstance(answer, Refusal) and answer.reason is Reason.BROKEN


def test_the_works_of_an_author_are_only_those_that_have_him():
    """Ручки людей у Google нет вовсе, и `inauthor:` он понимает как пожелание:
    замерено 23.08.2026 живьём — по `inauthor:"задача трех тел"` приезжают
    «The Three-Body Problem» Валтонена и Марчала, то есть чужие книги под
    видом работ автора.

    Поэтому автор проверяется по ответу: у тома он обязан быть."""
    payload = {"items": [
        {"id": "1", "volumeInfo": {"title": "Дюна",
                                   "authors": ["Фрэнк Герберт"]}},
        {"id": "2", "volumeInfo": {"title": "The Three-Body Problem",
                                   "authors": ["Mauri J. Valtonen"]}},
        {"id": "3", "volumeInfo": {"title": "Новая литература"}},
    ]}

    assert [hit.title for hit in parse_by_author(payload, "Фрэнк Герберт")] \
        == ["Дюна"]


def test_a_part_of_the_name_is_enough_to_own_the_book():
    """Человек набирает «толкин», а Google пишет его полным именем. Требовать
    совпадения целиком значило бы не находить по фамилии вовсе."""
    payload = {"items": [
        {"id": "1", "volumeInfo": {"title": "Властелин колец",
                                   "authors": ["Джон Рональд Руэл Толкин"]}},
    ]}

    assert [hit.title for hit in parse_by_author(payload, "толкин")] \
        == ["Властелин колец"]


def test_the_ladder_is_ordered_from_our_size_upwards():
    """Берём не самую крупную ступень, а ближайшую к нашей мерке 500×750 —
    решение пользователя 23.08.2026.

    Замерено в тот же день на семи издательских томах: `small` — 300×423,
    `medium` — 575×812, `large` — 800×1129, `extraLarge` — до 2448×3116.
    Ближайшая сверху `medium`: обрезка ужмёт её до 500×750 без растягивания, а
    `extraLarge` стоил бы двух мегабайт ради тех же 500 пикселей."""
    links = {"thumbnail": "t", "small": "s", "medium": "m",
             "large": "l", "extraLarge": "xl"}

    assert covers(links) == ["m", "l", "xl", "s", "t"]


def test_the_ladder_keeps_only_what_the_volume_declares():
    """У русских изданий ступень одна: замерено 23.08.2026 — у «Властелина
    Колец» издательства АСТ объявлен только `thumbnail` 128×195."""
    assert covers({"thumbnail": "t", "smallThumbnail": "st"}) == ["t"]
    assert covers({}) == []


def test_a_string_of_publishers_becomes_several_companies():
    """Google кладёт в `publisher` то одно издательство, то перечень: «ЛитРес,
    АСТ» встречается семь раз на 260 строк живой выдачи. Это два разных
    издательства — решение пользователя 23.08.2026, — и строкой они в базу
    попадать не должны: тогда книга АСТ и книга «ЛитРес, АСТ» лежат под разными
    издателями."""
    payload = {"id": "1", "volumeInfo": {"title": "Дюна",
                                         "publisher": "ЛитРес, АСТ"}}

    names = [one.name for one in parse_card(payload).companies]

    assert names == ["ЛитРес", "АСТ"]


def test_a_publisher_with_a_conjunction_stays_one_company():
    """«Манн, Иванов и Фербер» — одно издательство из трёх фамилий."""
    payload = {"id": "1", "volumeInfo": {
        "title": "Дюна", "publisher": "Манн, Иванов и Фербер"}}

    assert [one.name for one in parse_card(payload).companies] \
        == ["Манн, Иванов и Фербер"]


def test_the_isbn_of_a_volume_travels_with_the_row():
    """ISBN нужен запасному источнику обложек: по нему ищут издание, и им же
    сверяют, что нашлось то самое. Берётся тринадцатизначный, а при его
    отсутствии десятизначный — у Google бывают оба."""
    payload = {"items": [{"id": "1", "volumeInfo": {
        "title": "Пикник на обочине",
        "industryIdentifiers": [{"type": "ISBN_10", "identifier": "5170829833"},
                                {"type": "ISBN_13", "identifier": "9785170829835"}],
    }}]}

    hit = parse_search(payload)[0]

    assert [(one.source, one.value) for one in hit.external_ids] \
        == [(IdSource.ISBN, "9785170829835")]


def test_a_volume_without_an_isbn_carries_nothing():
    """У сканов и журналов ISBN нет вовсе — замерено, у восьми томов из десяти
    он есть, у двух нет."""
    payload = {"items": [{"id": "1", "volumeInfo": {"title": "Скан"}}]}

    assert parse_search(payload)[0].external_ids == ()
