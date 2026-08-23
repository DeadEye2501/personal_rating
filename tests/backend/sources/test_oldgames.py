"""Разбор страниц old-games.ru: выдача и карточка.

Единственный источник без API — разбирается HTML. Отсюда требование, которого
у остальных шести нет: **сломанная вёрстка обязана ломаться громко**, отказом и
записью в лог, а не тихо отдавать пустую карточку. Молчаливая потеря здесь
худший исход: перезапроса у игр не бывает вовсе."""

import httpx
import pytest

from backend.model import Found, GenreSource, Kind, Refusal, Source
from backend.sources.http import USER_AGENT, SourceHttp
from backend.sources.busy import ATTEMPTS
from backend.sources.oldgames.client import CARD, OldGamesClient
from backend.sources.oldgames.parse import parse_card, parse_search
from tests.conftest import counting, responding


async def searched(transport: httpx.MockTransport, query: str = "dune"):
    """Клиент на заданном транспорте, спрошенный один раз и закрытый."""
    client = OldGamesClient(SourceHttp("old_games", transport=transport))
    try:
        return await client.search(query, Kind.GAME)
    finally:
        await client.aclose()


def test_the_search_gives_a_row_for_every_game_on_the_page(fixture):
    """Строк ровно столько, сколько `id="game_N"` на странице.

    Число сверяется с самой страницей, а не с литералом: на этой вёрстке
    разборщик уже ошибался — наивный захват «до первого `</table>`» обрывается
    на таблице, вложенной внутрь строки, и даёт одну строку вместо семи."""
    page = fixture("oldgames/search_dune.txt")

    hits = parse_search(page)

    assert len(hits) == page.count('id="game_')
    assert len(hits) > 1, "фикстура с одной строкой ничего не сторожит"


def test_a_search_row_carries_what_the_page_shows(fixture):
    """Название, номер игры и год — из строки выдачи.

    Платформа и издатель со страницы не берутся: у кандидата выдачи для них нет
    поля, и разбирать их значило бы завести данные без потребителя."""
    hits = parse_search(fixture("oldgames/search_dune.txt"))

    dune = next(one for one in hits if one.source_id == "25")
    assert (dune.title, dune.year) == ("Dune", 1992)
    assert (dune.kind, dune.source) == (Kind.GAME, Source.OLD_GAMES)


def test_a_title_comes_from_the_attribute_and_not_from_the_broken_text(fixture):
    """Название берётся из атрибута ссылки, а не из её текста, и разница видна
    прямо на записанной странице: у игры 11045 название разбито тегом —
    `<b>Dune</b>: Keep The Secret`, — и склейка кусков через пробел даёт лишний
    пробел перед двоеточием.

    Отдельным тестом, а не строкой в соседнем: тот смотрит на «Dune», у которой
    `<b>` обнимает название целиком, и обе ветки дают там одно и то же —
    свойство наблюдалось ровно там, где оно неразличимо. Цена не косметическая:
    показываемое название уезжает в базу навсегда, перезапроса у игр не бывает."""
    hits = parse_search(fixture("oldgames/search_dune.txt"))

    secret = next(one for one in hits if one.source_id == "11045")
    assert secret.title == "Dune: Keep The Secret"


def test_a_second_title_stays_with_its_own_row(fixture):
    """У части игр в той же ячейке лежит `div.alt-titles-list` — второе
    написание. «Dune II» знают и как «Battle for Arrakis», и это единственный
    способ найти её по второму имени.

    Сверяются **все** строки, а не одна: на этой вёрстке пропущены закрывающие
    теги строк, строки вкладываются друг в друга, и поиск «вперёд по документу»
    отдавал трём строкам из семи чужое второе название. У «Dune» и «Dune 2000»
    своего нет вовсе, и пустота тут — предмет проверки, а не пропуск.

    Цена ошибки не косметическая: на этом поле стоит ключ автоматической
    склейки, и «Dune» с «Dune II» слились бы в одну игру."""
    hits = parse_search(fixture("oldgames/search_dune.txt"))

    assert {one.source_id: one.original_title for one in hits} == {
        "1345": "Dune Runner DOG",
        "25": "",
        "861": "",
        "1482": "Dune II: Battle for Arrakis",
        "11045": "",
        "2131": "Dune 3",
        "11350": "Дюна",
    }


def test_the_genre_travels_as_a_mark_of_this_source(fixture):
    """Жанр приезжает словом и уходит в справочник меткой своего пространства:
    колонка old-games.ru записана задачей 2, и `Adventure` сведён там в `Quest`
    сознательно."""
    hits = parse_search(fixture("oldgames/search_dune.txt"))

    dune = next(one for one in hits if one.source_id == "25")
    assert dune.genre_ext_ids == ((GenreSource.OLD_GAMES, "Adventure"),)


def test_the_search_carries_no_cover(fixture):
    """Обложки в выдаче нет вовсе — её добирает карточка. Пустая строка тут
    ответ, а не потеря: угадывать адрес нечем."""
    hits = parse_search(fixture("oldgames/search_dune.txt"))

    assert all(one.poster_url == "" for one in hits)


def test_nothing_found_is_an_empty_list_and_not_a_breakage(fixture):
    """Ноль строк — честный отрицательный ответ, в отличие от GOG. Страница при
    этом настоящая: таблица на месте, игр в ней нет."""
    assert parse_search(fixture("oldgames/search_nothing.txt")) == []


def test_a_page_that_is_not_a_listing_breaks_loudly(fixture):
    """Страница ошибки — не пустая выдача. Принять её за «ничего не нашлось»
    значит записать отрицательный факт по чужой странице."""
    with pytest.raises(ValueError, match="выдач"):
        parse_search(fixture("oldgames/missing_game.txt"))


def test_the_card_takes_its_name_from_the_game_and_not_from_the_site(fixture):
    """Ловушка микроразметки: первый `itemprop="name"` на странице — это
    «Old-Games.RU», имя самого сайта, а второй — «Каталог игр». Игра лежит
    третьей, внутри `itemscope` типа `SoftwareApplication`.

    Взятый без разбора, первый сделал бы все игры одноимёнными, и заметить это
    было бы нечем: поле не пустое."""
    card = parse_card(fixture("oldgames/card_dune.txt"), "25")

    assert card.item.title == "Dune"
    assert (card.item.source, card.item.source_id) == (Source.OLD_GAMES, "25")


def test_the_card_lays_the_two_names_out_by_language(fixture):
    """У карточки два имени, и раскладывает их язык, а не порядок на странице:
    `title` — язык оригинала либо русская локализация, `original_title` — всегда
    английское. Решение пользователя 03.08.2026.

    Свидетеля два, и они нарочно смотрят в разные стороны. У `Frank Herbert's
    Dune` главное имя английское, второе русское — поля **меняются местами**. У
    «Ил-2 Штурмовик» наоборот, и там перестановки быть не должно. С одним
    свидетелем «раскладываем по языку» неотличимо от «всегда меняем местами»."""
    swapped = parse_card(fixture("oldgames/card_frank_herberts_dune.txt"), "11350")
    assert swapped.item.title == "Дюна"
    assert swapped.item.original_title == "Frank Herbert's Dune"

    kept = parse_card(fixture("oldgames/card_il2.txt"), "14735")
    assert kept.item.title == "Ил-2 Штурмовик"
    assert kept.item.original_title == "IL-2 Sturmovik"


def test_every_second_name_is_looked_at_and_not_just_the_first(fixture):
    """Вторых имён на странице бывает несколько, каждое своим элементом, и брать
    первое попавшееся нельзя.

    Замерено: из 199 строк каталога второе имя есть у 81, и **у 28 из них их два
    и более** — треть. Свидетель: у `Bad Boys II` их два, `Bad Boys: Miami
    Takedown` и «Плохие парни II», и русское стоит вторым. Взяв первое, карточка
    теряет русское название навсегда — перезапроса у игр не бывает."""
    card = parse_card(fixture("oldgames/card_many_names.txt"), "11297")

    assert card.item.title == "Плохие парни II"
    assert card.item.original_title == "Bad Boys II"


def test_a_name_in_another_writing_is_not_the_english_one(fixture):
    """«Не русское» и «английское» — разные вещи, и поле обещает второе.

    У `Ankh: Pyramid No Nazo` второе имя японское,
    `アンク ピラミッドの謎`. Проверка «строка не русская» пропускает его в поле
    английского названия, и замерено, что таких строк у old-games 4 из 53.
    Магазины такого не отдают вовсе — там всё латиницей, — а третий источник не
    магазин."""
    card = parse_card(fixture("oldgames/card_japanese.txt"), "13380")

    assert card.item.title == "Ankh: Pyramid No Nazo"
    assert card.item.original_title == "Ankh: Pyramid No Nazo"


def test_an_english_name_stays_english_even_with_an_alias(fixture):
    """Если показываемое имя не русское, оно **и есть** английское, а второе имя
    при нём — псевдоним, и в поле английского названия ему не место.

    Свидетель замерен: у `D.O.G: Fight for Your Life` на странице **два** вторых
    имени, `DOG` и `Dune Runner`, и оба английские. Без этой проверки
    перестановка, потерявшая условие «второе имя русское», молча подменяла бы
    название псевдонимом — навсегда, перезапроса у игр не бывает."""
    card = parse_card(fixture("oldgames/card_two_english_names.txt"), "1345")

    assert card.item.title == "D.O.G: Fight for Your Life"
    assert card.item.original_title == "D.O.G: Fight for Your Life"


def test_a_russian_alias_does_not_reach_the_english_field(fixture):
    """Обратная сторона: у «Штырлица» второе имя тоже русское, и английского у
    игры нет. Поле остаётся пустым — оно обещает английское название, а не
    «второе, какое нашлось».

    Без этого свидетеля условие «второе имя не русское» не наблюдается вовсе:
    сними его, и в английское поле уехало бы «Штырлиц : Операция „Бюст“»."""
    card = parse_card(fixture("oldgames/card_two_russian_names.txt"), "8704")

    assert card.item.title == "Штырлиц"
    assert card.item.original_title == ""


def test_a_lone_english_name_fills_both_fields(fixture):
    """`original_title` у игры — **всегда** английское, и одинокое английское имя
    не исключение: у «Dune» второго нет, и оно же встаёт в оба поля. Решение
    пользователя 03.08.2026, замеченное им на этой самой игре."""
    card = parse_card(fixture("oldgames/card_dune.txt"), "25")

    assert card.item.title == "Dune"
    assert card.item.original_title == "Dune"


def test_a_lone_russian_name_leaves_the_english_field_empty(fixture):
    """Обратная сторона того же правила, и без неё «копируем одинокое имя»
    неотличимо от «копируем любое одинокое».

    Английского названия у «Ядерного титбита» нет вовсе: old-games находит его по
    «ядерный титбит» и **ничего** по «titbit», то есть имени нет не в этом
    ответе, а нигде. Пустое поле тут ответ, а не потеря: положи мы туда русское
    имя, поле стало бы врать о себе — оно обещает английское."""
    card = parse_card(fixture("oldgames/card_russian_only.txt"), "13363")

    assert card.item.title == "Ядерный титбит"
    assert card.item.original_title == ""


def test_the_card_carries_year_genre_and_synopsis(fixture):
    """Год берётся по подписи «Год выхода», жанр — из микроразметки, описание —
    из тела страницы: в микроразметке `description` лежит огрызок «Dune, Год
    выхода: 1992», а настоящий текст на четыре тысячи знаков стоит отдельно."""
    card = parse_card(fixture("oldgames/card_dune.txt"), "25")

    assert card.item.year == 1992
    assert card.genre_ext_ids == ((GenreSource.OLD_GAMES, "Adventure"),)
    assert len(card.item.synopsis) > 300
    assert "Атрейдес" in card.item.synopsis


def test_the_card_carries_both_studios_with_their_roles(fixture):
    """Разработчик и издатель различаются подписью, и у «Dune» они разные —
    Cryo и Virgin. Перепутанные местами, на одинаковых студиях они прошли бы
    молча."""
    card = parse_card(fixture("oldgames/card_dune.txt"), "25")

    assert [(one.name, str(one.role)) for one in card.companies] == [
        ("Cryo Interactive Entertainment", "developer"),
        ("Virgin Games", "publisher"),
    ]


def test_the_cover_comes_from_the_page(fixture):
    card = parse_card(fixture("oldgames/card_dune.txt"), "25")

    assert card.item.poster_url.endswith("/dune_cover.jpg")


def test_the_placeholder_cover_means_there_is_none(fixture):
    """У сайта своя заглушка вместо отсутствующей обложки. Записать её адресом
    значит завести карточку с картинкой «обложки нет» навсегда: перезапроса у
    игр не бывает."""
    card = parse_card(fixture("oldgames/card_without_cover.txt"), "4000")

    assert card.item.title == "Dedale"
    assert card.item.poster_url == ""


def test_an_unknown_studio_does_not_become_a_company(fixture):
    """«Разработчик неизвестен» оформлен у сайта настоящей компанией с именем
    `-` и своей ссылкой в каталог. Взятая как есть, она стала бы одной
    кликабельной студией на все такие игры разом — и навсегда: студии
    склеиваются по имени."""
    card = parse_card(fixture("oldgames/card_without_cover.txt"), "4000")

    assert card.companies == ()


def test_the_synopsis_drops_the_byline(fixture):
    """Под описанием стоит подпись автора обзора. В карточке она выглядела бы
    концом рассказа об игре, а к самой игре отношения не имеет."""
    card = parse_card(fixture("oldgames/card_dune.txt"), "25")

    assert "Автор обзора" not in card.item.synopsis
    assert card.item.synopsis.endswith(".")


def test_a_card_without_the_markup_breaks_loudly(fixture):
    """Страница ошибки под видом карточки — отказ, а не карточка с пустыми
    полями. Пустая карточка легла бы в базу навсегда."""
    with pytest.raises(ValueError, match="карточ"):
        parse_card(fixture("oldgames/missing_game.txt"), "99999999")


def test_a_card_without_a_name_breaks_loudly():
    """Разметка на месте, а имени в ней нет — тоже поломка: карточка без
    названия в библиотеке неотличима от испорченной."""
    page = (
        '<div itemscope itemtype="http://schema.org/SoftwareApplication">'
        '<span itemprop="applicationSubCategory">RPG</span></div>'
    )

    with pytest.raises(ValueError, match="назван"):
        parse_card(page, "1")


async def test_the_client_finds_games(replay):
    found = await searched(replay("oldgames/search_dune.txt"))

    assert isinstance(found, Found)
    assert any(one.title == "Dune" for one in found.value)


async def test_an_empty_listing_is_an_empty_answer(replay):
    """Ноль строк — пустая выдача, а не отказ: страница настоящая, игр в ней
    нет. Так же отвечает и Steam, и разбирать этот случай по-своему незачем."""
    found = await searched(replay("oldgames/search_nothing.txt"))

    assert found == Found([])


async def test_a_broken_page_becomes_a_refusal_with_a_trace(caplog):
    """Наружу из клиента исключение не вылетает: разбор сорвался — отказ и
    запись, по которой потом ищут причину.

    Код при этом 200: под чужим кодом отказ собрался бы раньше разбора, и
    проверка прошла бы, не дойдя до проверяемого места."""
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, text="<html><body>не выдача</body></html>")
    )

    with caplog.at_level("WARNING"):
        found = await searched(transport)

    assert isinstance(found, Refusal)
    assert "old_games" in caplog.text


def busy(page: str, times: int):
    """Транспорт, отвечающий `503` заданное число раз, а потом страницей.

    Счёт запросов берётся общим `counting`: без счёта «повторил» неотличимо от
    «попал с первого раза»."""
    served = []

    def handler(request: httpx.Request) -> httpx.Response:
        served.append(request)
        if len(served) <= times:
            return httpx.Response(503, text="<html>Service Unavailable</html>")
        return httpx.Response(200, text=page)

    return counting(httpx.MockTransport(handler))


async def test_a_busy_answer_is_repeated_at_once(fixture):
    """`503` у этого сайта — «занят сейчас», а не отказ: следующий же запрос
    проходит за обычное время. Значит повтор идёт немедленно, без пауз."""
    transport, asked = busy(fixture("oldgames/search_dune.txt"), times=1)

    found = await searched(transport)

    assert isinstance(found, Found), "повтора не было"
    assert len(asked) == 2, "запрос ушёл не дважды"


async def test_a_busy_source_is_not_shut_off_by_the_breaker(fixture):
    """Главная ловушка этого источника. `503` — штатный ответ на большой
    выдаче; утечёт он в предохранитель, и источник замолкнет на пятнадцать
    секунд после каждого поиска.

    Проверяется следствие, а не объявление: после пачки `503` клиент отвечает
    на следующий вопрос, а не отдаёт «предохранитель взведён»."""
    transport, _ = busy(fixture("oldgames/search_dune.txt"), times=ATTEMPTS)
    http = SourceHttp("old_games", transport=transport)
    client = OldGamesClient(http)

    given_up = await client.search("dune", Kind.GAME)
    again = await client.search("dune", Kind.GAME)
    await client.aclose()

    assert isinstance(given_up, Refusal)
    assert not http.breaker.is_open(), "предохранитель взведён штатным 503"
    assert isinstance(again, Found), "источник замолчал после большой выдачи"


async def test_the_repeat_is_not_endless():
    """Повтор не вечен: при настоящей беде клиент сдаётся отказом, а не
    крутится. Считаются запросы — без счёта вечный цикл выглядел бы как
    зависание, а не как поломка."""
    transport, asked = counting(
        responding(503, text="<html>Service Unavailable</html>"))

    found = await searched(transport)

    assert isinstance(found, Refusal)
    # Число литералом, а не из `ATTEMPTS`: сверка с объявлением зеленела бы при
    # любом значении, в том числе при десяти.
    assert len(asked) == 3


async def test_the_search_asks_the_catalog_with_the_query(fixture):
    """Адрес и довод запроса — то, чего не сторожит ни один разбор: подмени
    путь, и все проверки разбора останутся зелёными, а живой поиск замолчит.
    Этим дефектом GOG был сломан целиком при 905 зелёных тестах.

    Кириллица проверяется тем же запросом: она работает там, где заведено
    русское название, и искажённая при сборке молча искала бы не то."""
    transport, asked = counting(
        responding(200, text=fixture("oldgames/search_nothing.txt")))

    await searched(transport, query="дюна")

    assert asked[0].url.path == "/catalog/"
    assert asked[0].url.params["gamename"] == "дюна"
    # Честный `User-Agent`, а не браузерный: фильтра по нему у сайта нет, а если
    # мы однажды начнём мешать, у них будет способ написать, а не забанить молча.
    assert asked[0].headers["user-agent"] == USER_AGENT


async def test_the_card_is_asked_by_its_own_address(fixture):
    """Половина клиента, которую не звал ни один тест. Подмени шаблон адреса —
    и карточка не приедет никогда, а разбор останется зелёным."""
    transport, asked = counting(
        responding(200, text=fixture("oldgames/card_dune.txt")))
    client = OldGamesClient(SourceHttp("old_games", transport=transport))
    found = await client.card("25", Kind.GAME)
    await client.aclose()

    assert isinstance(found, Found)
    assert found.value.item.title == "Dune"
    assert asked[0].url.path == "/game/25.html"
    assert CARD.format(source_id="25").endswith("/game/25.html")


async def test_a_card_the_site_does_not_have_is_a_refusal(replay):
    """Несуществующий номер отдаёт 404 со страницей ошибки. Отрицательным
    фактом это не становится: номер к нам приходит из выдачи, и его отсутствие
    означает беду, а не «такой игры нет»."""
    client = OldGamesClient(SourceHttp(
        "old_games", transport=replay("oldgames/missing_game.txt")))
    found = await client.card("99999999", Kind.GAME)
    await client.aclose()

    assert isinstance(found, Refusal)


async def test_a_broken_card_becomes_a_refusal_with_a_trace(caplog):
    """Разбор карточки сорвался — отказ и запись, а не карточка с пустыми
    полями: пустая легла бы в базу навсегда."""
    client = OldGamesClient(SourceHttp("old_games", transport=responding(
        200, text="<html><body>не карточка</body></html>")))
    with caplog.at_level("WARNING"):
        found = await client.card("25", Kind.GAME)
    await client.aclose()

    assert isinstance(found, Refusal)
    assert "old_games" in caplog.text
