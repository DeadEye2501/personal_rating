"""Deezer: восьмой источник и единственный, откуда приходит музыка.

Главная его особенность замерена живьём 22.08.2026: **отказ приходит под
успешным кодом**. Волна из 240 запросов дала `HTTP 200` у всех, а у 177 в теле
лежало `{"error": {"code": 4}}`. Клиент, смотрящий на код ответа, записал бы в
базу пустой альбом со свежим `synced_at` — то есть перезапроса не случилось бы
никогда.

Тем же способом отличает отсутствие Steam: `success` внутри `200`."""

from contextlib import aclosing
from datetime import timedelta

import httpx

from backend.model import (
    SEARCH_SIZE,
    Found,
    GenreSource,
    Kind,
    Missing,
    PersonRole,
    Reason,
    Refusal,
    Source,
)
from backend.sources.deezer.client import DeezerClient
from backend.sources.deezer.parse import parse_albums, parse_artists, parse_card
from backend.sources.http import SourceHttp
from tests.conftest import FakeClock, counting, responding

# Отказ по частоте записать нечем: он приходит только на волну одновременных
# запросов. Тело — дословно замеренное 22.08.2026.
BUSY_BODY = {"error": {"type": "Exception",
                       "message": "Quota limit exceeded", "code": 4}}


def client(transport: httpx.MockTransport) -> DeezerClient:
    """Ключа Deezer не требует вовсе — как Steam, GOG и old-games.ru."""
    return DeezerClient(SourceHttp("deezer", transport=transport))


async def carded(transport: httpx.MockTransport, source_id: str = "54717452"):
    async with aclosing(client(transport)) as one:
        return await one.card(source_id, Kind.MUSIC)


def test_the_search_gives_a_row_for_every_album(fixture):
    """Строк ровно столько, сколько альбомов в `data`: обрезанная выдача
    выглядела бы как бедный каталог, а не как поломка разбора."""
    payload = fixture("deezer/search_album_kino.json")

    hits = parse_albums(payload)

    assert len(hits) == len(payload["data"])
    assert len(hits) > 1, "фикстура с одной строкой ничего не сторожит"


def test_a_search_row_carries_what_the_album_shows(fixture):
    """Название, номер альбома и тип содержимого. Перепутай тип — и альбом уехал
    бы в чужую вкладку, а вкладка у этого проекта первичный фильтр."""
    first = parse_albums(fixture("deezer/search_album_kino.json"))[0]

    assert (first.kind, first.source) == (Kind.MUSIC, Source.DEEZER)
    assert first.source_id == "54717452"
    assert first.title == "Группа крови"


def test_a_row_takes_the_only_genre_the_search_gives(fixture):
    """В строке выдачи жанр один и лежит числом в `genre_id`, а список `genres`
    приходит только в карточке. Терять его незачем: без метки строка стоит без
    жанра вовсе."""
    first = parse_albums(fixture("deezer/search_album_kino.json"))[0]

    assert first.genre_ext_ids == ((GenreSource.DEEZER, "152"),)


def test_an_album_without_a_genre_carries_none():
    """Замерено: у альбома без жанра `genre_id` равен `-1`, а не пустоте.
    Записанный как есть, он ушёл бы в справочник меткой, которой у Deezer нет."""
    without = {"data": [{"id": 1, "title": "Без жанра", "genre_id": -1}]}

    assert parse_albums(without)[0].genre_ext_ids == ()


def test_the_tracks_keep_the_order_of_the_album(fixture):
    """Замерено: `track_position` во вложенном списке приходит пустым у всех
    треков — у «Группы крови» все `None`. Настоящие номера есть только в
    отдельной ручке, и раз порядок значения не имеет, ручка не нужна: порядок
    берётся по месту в списке."""
    payload = fixture("deezer/album_blood_type.json")

    card = parse_card(payload)

    assert list(card.tracks) == [one["title"] for one in payload["tracks"]["data"]]
    assert len(card.tracks) > 1, "фикстура с одним треком порядка не сторожит"


def test_the_performer_stands_where_the_director_stands(fixture):
    """Решение пользователя 22.08.2026: вместо режиссёра — исполнитель, вместо
    актёров — треки. Трек человеком не является вовсе и в титры не попадает —
    иначе «Группа крови» предлагалась бы в подсказке при вводе имени."""
    card = parse_card(fixture("deezer/album_blood_type.json"))

    assert [one.name for one in card.people] == ["Кино"]
    assert [one.role for one in card.people] == [PersonRole.PERFORMER]
    assert card.people[0].source is Source.DEEZER
    assert card.people[0].source_id == "4505880"


def test_the_label_never_becomes_a_company(fixture):
    """Решение пользователя 22.08.2026: лейбл не берётся. Замерено, почему:
    `label` у Deezer — не имя лейбла, а список правообладателей, обрезанный
    сервисом на сотне знаков."""
    payload = fixture("deezer/album_blood_type.json")

    assert payload["label"], "фикстура без лейбла ничего не сторожит"
    assert parse_card(payload).companies == ()


def test_every_genre_number_reaches_the_card_untouched():
    """Отсев незнакомого — работа справочника, а не разбора: у Deezer 210
    жанров, в справочнике 21, и решает, какие из них жанр, таблица правил.
    Отсей их здесь — и правило «список закрытый» держалось бы двумя местами
    сразу, а разошлись бы они молча."""
    payload = {"id": "1", "title": "А", "artist": {"id": "2", "name": "Б"},
               "genres": {"data": [{"id": 152}, {"id": 1234}]}}

    marks = parse_card(payload).genre_ext_ids

    assert (GenreSource.DEEZER, "152") in marks
    assert (GenreSource.DEEZER, "1234") in marks, (
        "разбор чужого не отсеивает — это работа справочника")


def test_an_album_without_genres_gets_no_marks(fixture):
    """Замерено: у 12 альбомов из 57 список жанров пуст. Карточка обязана
    собраться — альбом без жанра это не поломка."""
    card = parse_card(fixture("deezer/album_no_genre.json"))

    assert card.genre_ext_ids == ()
    assert card.item.title


def test_the_cover_is_the_extra_large_square(fixture):
    """1000×1000, и это квадрат, а не афиша: рамку под него расширяет задача 7.
    Берётся готовым адресом — собирать тут нечего, поле читается как есть."""
    card = parse_card(fixture("deezer/album_blood_type.json"))

    assert "1000x1000" in card.item.poster_url


def test_the_year_comes_from_the_release_date(fixture):
    """Год берётся как есть, и цена известна: замерено, что у трёх альбомов из
    шести он неверен, промах доходит до сорока четырёх лет. Чинил бы это второй
    источник, а второго нет — решение пользователя 22.08.2026."""
    card = parse_card(fixture("deezer/album_blood_type.json"))

    assert card.item.year == 1988


async def test_a_refusal_inside_a_two_hundred_is_not_an_empty_album():
    """Главная ловушка источника. Клиент, смотрящий на код ответа, записал бы в
    базу пустой альбом — и `synced_at` у него был бы свежий, то есть
    перезапроса не случилось бы никогда.

    Предохранитель взводится тем же сроком: без него следующая карточка
    прокрутки идёт в тот же отказ."""
    http = SourceHttp("deezer", transport=responding(json=BUSY_BODY))

    answer = await DeezerClient(http).card("54717452", Kind.MUSIC)

    assert isinstance(answer, Refusal) and answer.reason is Reason.RATE
    assert http.breaker.is_open()


async def test_no_data_inside_a_two_hundred_is_a_missing_album(replay):
    """Обратная половина: `code: 800` — это «такого у меня нет», и оно обязано
    стать `Missing`, а не отказом. Отличаются они телом, а не кодом: у обоих
    `HTTP 200`."""
    assert isinstance(await carded(replay("deezer/absent.json")), Missing)


async def test_an_unknown_error_code_is_not_taken_for_absence():
    """Отрицательный факт пишется по **известному** коду ошибки, а не по любому:
    записанное «такого нет» живёт неделю, и незнакомая беда, принятая за
    отсутствие, стёрла бы альбом из выдачи на всё это время."""
    answer = await carded(responding(json={"error": {"code": 999,
                                                     "message": "что-то"}}))

    assert isinstance(answer, Refusal) and answer.reason is Reason.BROKEN


async def test_the_source_speaks_again_a_minute_after_a_rate_refusal():
    """Срок отката назван минутой, и это замер, а не догадка: 120 запросов
    подряд за 16.5 с проходят целиком, срывается только залп одновременных —
    Deezer отпускает за секунды.

    Наблюдается следствием, а не числом в отказе: до минуты источник молчит,
    после — отвечает снова. Возьми клиент суточный срок, как у квоты Google, и
    музыка пропала бы из поиска до полуночи из-за одного залпа."""
    clock = FakeClock()
    http = SourceHttp("deezer", clock=clock, transport=responding(json=BUSY_BODY))

    async with aclosing(DeezerClient(http)) as one:
        await one.card("54717452", Kind.MUSIC)

        assert http.breaker.is_open()
        clock.advance(timedelta(seconds=59))
        assert http.breaker.is_open(), "источник открылся раньше срока"
        clock.advance(timedelta(seconds=2))
        assert not http.breaker.is_open(), "источник молчит дольше минуты"


async def test_the_body_decides_before_the_code():
    """Порядок «сначала тело, потом код» — всё содержание этого клиента, и
    наблюдается он только там, где тело и код говорят разное.

    Свидетель — отказ по частоте под чужим кодом: разберись код первым, и
    вместо `RATE` приехал бы `BROKEN`, а предохранитель не взвёлся бы вовсе —
    то есть следующая карточка прокрутки пошла бы в тот же залп."""
    http = SourceHttp("deezer", transport=responding(500, json=BUSY_BODY))

    async with aclosing(DeezerClient(http)) as one:
        answer = await one.card("54717452", Kind.MUSIC)

    assert isinstance(answer, Refusal) and answer.reason is Reason.RATE
    assert http.breaker.is_open(), "предохранитель не взведён"


async def test_an_error_that_is_not_an_object_becomes_a_refusal():
    """Форма ошибки у Deezer объявлена объектом, и все замеренные такие. Придёт
    строкой — классифицировать нечем, и это отказ, а не исключение: `error.get`
    уронил бы `AttributeError` мимо обеих обёрток, и через границу потоков
    ушла бы трассировка вместо названной жалобы."""
    answer = await carded(responding(json={"error": "перегрев"}))

    assert isinstance(answer, Refusal) and answer.reason is Reason.BROKEN
    assert answer.detail.startswith("ошибка не объект"), answer.detail


async def test_a_body_that_is_not_an_object_becomes_a_refusal():
    """То же самое ярусом выше: разобравшееся тело бывает и списком — так
    отвечает прокси, подставивший свой ответ. `payload.get` уронил бы
    `AttributeError` там, где ловить его некому."""
    answer = await carded(responding(json=[{"id": 1}]))

    assert isinstance(answer, Refusal) and answer.reason is Reason.BROKEN
    assert answer.detail == "тело не объект", answer.detail


async def test_the_search_asks_the_album_handle(fixture):
    """Адрес и доводы запроса — то, чего не сторожит ни один разбор: подмени
    путь, и все проверки разбора останутся зелёными, а живой поиск замолчит.
    Этим дефектом GOG был сломан целиком при 905 зелёных тестах."""
    transport, asked = counting(
        responding(json=fixture("deezer/search_album_kino.json")))
    one = client(transport)

    await one.search("группа крови", Kind.MUSIC)
    await one.aclose()

    url = asked[0].url
    assert url.path == "/search/album"
    assert url.params.get("q") == "группа крови"
    assert url.params.get("limit") == str(SEARCH_SIZE)


async def test_the_second_portion_is_asked_from_the_shift(fixture):
    """Смещение обязано доехать до самого запроса, а не только до сервиса:
    замени `index` константой — и лента догружала бы одну и ту же первую
    двадцатку без конца, а прокрутка выглядела бы застрявшей.

    У Deezer `index` — это смещение буквально; вторая порция записана слайсом 1
    ровно под эту проверку."""
    transport, asked = counting(
        responding(json=fixture("deezer/search_album_page2.json")))
    one = client(transport)

    answer = await one.search("rock", Kind.MUSIC, SEARCH_SIZE)
    await one.aclose()

    assert isinstance(answer, Found) and answer.value
    assert asked[0].url.params.get("index") == str(SEARCH_SIZE)


async def test_the_first_portion_starts_at_the_beginning(fixture):
    """Обратная половина: без смещения выдача начинается с нуля. Без неё
    «доехало» неотличимо от «уехало всегда»."""
    transport, asked = counting(
        responding(json=fixture("deezer/search_album_kino.json")))
    one = client(transport)

    await one.search("кино", Kind.MUSIC)
    await one.aclose()

    assert asked[0].url.params.get("index") == "0"


async def test_the_card_is_asked_by_the_album_identifier(fixture):
    """Карточка идёт своей ручкой: треки и полный список жанров есть только у
    неё — в строке выдачи лежит один жанр числом и ни одного трека."""
    transport, asked = counting(
        responding(json=fixture("deezer/album_blood_type.json")))

    await carded(transport, "54717452")

    assert asked[0].url.path == "/album/54717452"


async def test_the_artists_of_a_name_come_from_the_search(fixture):
    """У исполнителя идентичность настоящая, и ищется он своей ручкой — так же,
    как человек у TMDB. Найденные приезжают все: отбора среди найденных снаружи
    людей нет, правило от 31.07.2026."""
    transport, asked = counting(
        responding(json=fixture("deezer/search_artist_kino.json")))
    one = client(transport)

    answer = await one.find_people("Кино")
    await one.aclose()

    assert isinstance(answer, Found) and answer.value
    assert answer.value[0].source_id == "4505880"
    assert asked[0].url.path == "/search/artist"
    assert asked[0].url.params.get("q") == "Кино"


async def test_the_albums_of_an_artist_come_by_identity(fixture):
    """У Deezer идентичность исполнителя настоящая — `artist.id`, — и
    спрашивать его по имени значило бы притащить тёзок туда, где их быть не
    должно. Наблюдается спрошенным адресом, а не выдачей: выдача одинакова у
    обоих путей, а путь — нет."""
    transport, asked = counting(
        responding(json=fixture("deezer/artist_albums_kino.json")))
    one = client(transport)

    answer = await one.credits_of("4505880", Kind.MUSIC)
    await one.aclose()

    assert isinstance(answer, Found) and answer.value
    assert asked[0].url.path == "/artist/4505880/albums"
    # Размер просится явно и числом, а не из `ALL_ALBUMS`: сверка с объявлением
    # зеленела бы при любом его значении, включая умолчание ручки — 25 строк с
    # `next`, замерено 23.08.2026: у Мадонны 25 из 72, у Элвиса 25 из 42.
    # Порции у этого жеста нет ни в бэкенде, ни на странице, и до обрезанного
    # хвоста человек не добрался бы ничем.
    #
    # Тысяча, потому что предел ручки на ней не заканчивается: замерено там же,
    # `limit=1000` отвечает так же и без ошибки.
    assert asked[0].url.params.get("limit") == "1000"


def test_a_row_of_an_artist_album_carries_its_year(fixture):
    """Год в строке выдачи есть у одной ручки из двух: у альбомов исполнителя
    он стоит у каждой строки, а в поиске его нет вовсе — замерено 23.08.2026.

    Читается он поэтому по наличию, и без него карточка «Легенды» показалась бы
    человеку без года, хотя источник его назвал."""
    rows = parse_albums(fixture("deezer/artist_albums_kino.json"))

    assert [one.year for one in rows][:3] == [2025, 2022, 2021]


def test_an_artist_row_carries_the_identity_and_nothing_else(fixture):
    """Строка человека несёт только идентичность: имя, картинка и число
    альбомов не нужны никому — по номеру спрашивается фильмография, и она уже
    несёт всё, что покажут."""
    people = parse_artists(fixture("deezer/search_artist_kino.json"))

    assert [one.source_id for one in people][:1] == ["4505880"]
    assert len(people) == len(fixture("deezer/search_artist_kino.json")["data"])


async def test_a_code_outside_two_hundred_is_a_refusal():
    """Тело разбирается до кода, но код не игнорируется вовсе.

    Свидетель — **разбираемое** тело под чужим кодом, и спрашивается им
    **поиск**, а не карточка: у карточки пустое тело роняет разбор (`KeyError`
    по `id`), отказ приходит из него, и проверку кода можно было бы снять
    целиком, не уронив ни одного теста. У поиска пустой `data` разбирается
    успешно — снятая проверка кода превратила бы `500` в `Found([])`, то есть в
    «источник ответил, ничего не нашлось», молча."""
    one = client(responding(500, json={"data": []}))
    try:
        answer = await one.search("группа крови", Kind.MUSIC)
    finally:
        await one.aclose()

    assert isinstance(answer, Refusal), "чужой код принят за пустую выдачу"
    assert answer.reason is Reason.BROKEN


def test_a_single_is_marked_and_the_row_stays_in_the_answer():
    """Приложение оценивает альбомы, и сингл в нём не строка выдачи, а мусор:
    замерено 23.08.2026 живьём — по «дельфин» из двадцати строк семь помечены
    `single`, у шести ровно один трек, и называются они словом запроса, но
    исполнители там чужие.

    Разбор его **помечает**, а выбрасывает сервис: полноту порции он считает по
    сырому ответу источника, и укоротивший её отсев объявил бы двадцатую строку
    последней. Тип записи называет сам источник — гадать по числу треков не
    нужно."""
    payload = {"data": [
        {"id": 1, "title": "Группа крови", "record_type": "album"},
        {"id": 2, "title": "Дельфин", "record_type": "single"},
        {"id": 3, "title": "Хлопок и Нейтрино", "record_type": "ep"},
    ]}

    assert [(hit.title, hit.single) for hit in parse_albums(payload)] == [
        ("Группа крови", False),
        ("Дельфин", True),
        ("Хлопок и Нейтрино", False),
    ]


def test_a_row_without_a_record_type_is_not_a_single():
    """Незнакомый ответ синглом не считается: меткой служит названное синглом, а
    не отсутствие слова «альбом» — иначе смена словаря у источника вычистила бы
    выдачу целиком."""
    payload = {"data": [{"id": 1, "title": "Без типа"}]}

    assert [(hit.title, hit.single) for hit in parse_albums(payload)] \
        == [("Без типа", False)]
