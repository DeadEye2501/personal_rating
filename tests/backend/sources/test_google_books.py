"""Google Books: седьмой источник и единственный, откуда приходят книги.

Главная его ловушка замерена живьём 22.08.2026: `503` — это «занят сейчас», а
не «не нашёл». Прогон без повтора нашёл 5 книг из 10, с повтором — 8, и все пять
потерь были занятостью. Считать её пустой выдачей значит терять половину
каталога при зелёном наборе."""

import asyncio
from datetime import timedelta

from contextlib import aclosing

import httpx

from backend.model import (
    SEARCH_SIZE,
    Found,
    Kind,
    Missing,
    Reason,
    Refusal,
)
from backend.sources.backoff import until_midnight
from backend.sources.busy import ATTEMPTS
from backend.sources.google_books.client import GoogleBooksClient
from backend.sources.http import SourceHttp
from tests.backend.sources.conftest import keys_of, keys_of_google
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


async def test_a_busy_source_is_asked_three_times_and_no_more(replay):
    """Повтор не вечен: при настоящей беде клиент отказывает, а не долбится.

    Число литералом, а не из `ATTEMPTS`: сверка с объявлением зеленела бы при
    любом значении — в том числе при десяти, то есть тридцати запросах на одну
    книгу из суточной тысячи."""
    transport, asked = counting(replay("google_books/busy.json"))

    answer = await searched(transport)

    assert isinstance(answer, Refusal) and answer.reason is Reason.RATE
    assert len(asked) == 3


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
    transport, seen = keys_of_google("кончился")
    http = SourceHttp("google_books", transport=transport)
    client = GoogleBooksClient(http, ("кончился", "запасной"))

    first = await client.search("дюна", Kind.BOOK)
    second = await client.search("герберт", Kind.BOOK)

    assert isinstance(first, Found), "запасной ключ не подставился"
    assert isinstance(second, Found)
    assert not http.breaker.is_open(), "источник закрыт, хотя ключ ещё есть"
    # Исчерпанный ключ спрашивают один раз: возвращаться к нему до полуночи
    # значит тратить по походу в сеть на каждом запросе.
    assert keys_of(seen) == ["кончился", "запасной", "запасной"]


async def test_both_racing_requests_get_through_on_the_spare_key():
    """Карточка и работы тёзок грузятся разом одним клиентом, и на исчерпанной
    квоте `429` приходит обоим — это штатный путь книжного поиска, а не
    редкость.

    Проигравший гонку повторяет тем ключом, который сосед уже поставил.
    Откажи он — отказ по квоте закрыл бы источник до полуночи, и вторым ключом
    не было бы спрошено ни одного запроса: победитель получил бы «предохранитель
    взведён» на своём же повторе.

    Наблюдается ключами на проводе: обоим ответили выдачей и обоих спросили
    запасным."""
    # Задержка ответа исчерпанного ключа: без неё оба запроса уходят по
    # очереди, и гонки не выйдет вовсе.
    transport, seen = keys_of_google("кончился", delay=0.01)
    http = SourceHttp("google_books", transport=transport)
    client = GoogleBooksClient(http, ("кончился", "запасной"))

    async with aclosing(client):
        first, second = await asyncio.gather(
            client.search("дюна", Kind.BOOK),
            client.credits_of("Фрэнк Герберт", Kind.BOOK),
        )

    keys = keys_of(seen)
    assert keys[:2] == ["кончился", "кончился"], "гонки не вышло, ключи по очереди"
    assert isinstance(first, Found), "выдача отказала на исчерпанном ключе"
    assert isinstance(second, Found), "работы автора отказали на исчерпанном ключе"
    assert not http.breaker.is_open(), "источник закрыт, хотя ключ ещё есть"
    assert keys.count("запасной") == 2, f"запасным спрошено не всё: {keys}"


async def test_the_first_key_is_asked_again_the_next_day():
    """Квота суточная, и в полночь оживает не только предохранитель, но и
    первый ключ. Не вернись к нему номер — со вторых суток запас ключей равен
    одному: спрашивается последний, а исчерпав его, источник закрывается, ни
    разу не попробовав ключ с полной квотой. Окно приложения живёт открытым
    сутками, так что случай штатный.

    Наблюдается ключами на проводе: после полуночи первый спрошен снова."""
    clock = FakeClock()
    transport, seen = keys_of_google("вчерашний")
    http = SourceHttp("google_books", clock=clock, transport=transport)
    client = GoogleBooksClient(http, ("вчерашний", "запасной"))

    async with aclosing(client):
        await client.search("дюна", Kind.BOOK)
        clock.advance(until_midnight(clock()) + timedelta(minutes=1))
        await client.search("герберт", Kind.BOOK)

    assert keys_of(seen) == ["вчерашний", "запасной", "вчерашний",
                             "запасной"], keys_of(seen)


async def test_a_client_without_keys_asks_with_an_empty_one():
    """Ключей может не быть вовсе: переменная в `.env` пустая, и `load_config`
    отдаёт пустой набор. Тогда ключ на проводе пустой, Google отвечает `400`, и
    человек читает «ключ не принят» — то же, что при негодном.

    Подставь клиент что угодно другое, и вместо понятной жалобы приехала бы
    «кончилась квота»: без ключа вовсе ручка отвечает `429`."""
    transport, asked = counting(responding(json={"items": []}))

    async with aclosing(GoogleBooksClient(
            SourceHttp("google_books", transport=transport), ())) as one:
        await one.search("дюна", Kind.BOOK)

    assert asked[0].url.params.get("key") == ""


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


















