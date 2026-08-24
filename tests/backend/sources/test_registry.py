"""Реестр держится на том, что контракт у всех клиентов один."""

import inspect
from datetime import timedelta
from pathlib import Path

import httpx
import pytest

from backend.config import load_config
from backend.model import SEARCH_SIZE, Found, Kind, Refusal, Source
from backend.sources.gog.client import GogClient
from backend.sources.oldgames.client import OldGamesClient
from backend.sources.ratings.kinopoisk.client import KinopoiskClient
from backend.sources.ratings.mdblist.client import MdbListClient
from backend.sources.ratings.omdb.client import OmdbClient
from backend.sources.build import build_sources
from backend.sources.registry import ROUTES
from backend.sources.steam.client import SteamClient
from backend.sources.tmdb.client import TmdbClient
from backend.unique import unique
from tests.backend.sources.conftest import key_of, keys_of, keys_of_google
from tests.conftest import counting, responding

# Кто держит каталог и по какому типу его спрашивают — выведено из таблицы
# маршрутов, а не переписано списком: переписанный расходится не с ожидаемым, а
# с самим собой, и новый источник остаётся непроверенным при зелёном наборе.
CATALOG_OWNERS = tuple(unique(name for route in ROUTES.values()
                              for name in route.catalogs))
KIND_OF = {name: kind for kind, route in ROUTES.items()
           for name in route.catalogs}

SILENT = responding(json={})


def sources():
    return build_sources(
        load_config({"TMDB_API_KEY": "k"}, base_dir=Path(".")), transport=SILENT
    )


@pytest.fixture
async def registry():
    """Поднятый реестр, закрывающий себя сам.

    Закрытие в разборке, а не строкой в конце каждого теста: упавший до
    `aclose` тест оставлял бы соединения открытыми, и заметить это было бы
    нечем — падение он объяснит своей причиной."""
    made = sources()
    yield made
    await made.aclose()


def keyed():
    """Настройки, где у каждого источника свой различимый ключ."""
    return load_config(
        {
            "TMDB_API_KEY": "tmdb-key",
            "GOOGLE_BOOKS_API_KEY": "google-books-key",
            "GOOGLE_BOOKS_API_KEY_2": "google-books-spare",
            "MDBLIST_API_KEY": "mdblist-key",
            "OMDB_API_KEY": "omdb-key",
            "POISKKINO_API_KEY": "poiskkino-key",
            "KINOPOISK_UNOFFICIAL_API_KEY": "unofficial-key",
        },
        base_dir=Path("."),
    )


async def test_films_and_series_come_from_tmdb(registry):
    for kind in (Kind.MOVIE, Kind.SERIES):
        assert [type(one) for one in registry.catalog_for(kind)] == [TmdbClient], kind


async def test_games_come_from_three_equal_sources(registry):
    """Покрытие даёт сумма трёх, а не каждый по отдельности: Steam и GOG —
    витрины и знают только то, что продаётся сегодня, old-games.ru закрывает
    ретро, которого в витринах нет вовсе."""
    # Список, а не множество: порядок задаёт, чью выдачу человек увидит первой
    # при равном числе кандидатов, а множество обмен источников местами скрывает.
    assert [type(one) for one in registry.catalog_for(Kind.GAME)] == [
        SteamClient,
        GogClient,
        OldGamesClient,
    ]


async def test_films_ask_three_aggregators(registry):
    assert {type(one) for one in registry.rating_sources(Kind.MOVIE)} == {
        MdbListClient,
        OmdbClient,
        KinopoiskClient,
    }


@pytest.mark.parametrize("kind", [Kind.MOVIE, Kind.SERIES])
async def test_films_and_series_ask_the_same_three(registry, kind):
    """Список задан явно, а не сравнением двух вызовов между собой: у кино и
    сериалов в реестре один и тот же `return`, и такое сравнение сходилось бы при
    любой реализации, включая пустую."""
    assert [type(one) for one in registry.rating_sources(kind)] == [
        MdbListClient, OmdbClient, KinopoiskClient
    ]


async def test_games_ask_nobody_for_ratings(registry):
    """Оценки критиков у игр приходят даром: Metascore от Steam, своя от GOG.
    Отдельного источника нет и не нужно — ни ключа, ни запроса, ни квоты."""
    assert registry.rating_sources(Kind.GAME) == []


@pytest.mark.parametrize("kind", [Kind.MOVIE, Kind.SERIES])
async def test_people_are_searched_at_tmdb(registry, kind):
    """Тождеством, а не типом: клиент должен быть тот же самый, что и в
    каталоге, — второй такой же уехал бы в сеть со своим предохранителем."""
    assert registry.people_for(kind) is registry.tmdb


async def test_games_ask_nobody_about_people(registry):
    """Замерено: Steam по разработчику отдаёт разметку витрины, GOG молча
    игнорирует параметр и возвращает весь каталог. Людей магазины не отдают
    вовсе, только компании."""
    assert registry.people_for(Kind.GAME) is None


async def test_books_are_searched_at_google(registry):
    """Источник книг один: у Open Library народная разметка, а Goodreads закрыл
    выдачу ключей в 2020.

    Тождеством, а не типом: клиент обязан быть тот же самый, что поднят
    сборкой, — второй такой же уехал бы в сеть со своим предохранителем и со
    своей квотой в тысячу запросов."""
    assert registry.catalog_for(Kind.BOOK) == [registry.google_books]


async def test_the_author_of_a_book_is_asked_at_google(registry):
    """Тождеством, а не типом: ответчик за людей обязан быть тем же клиентом,
    что и каталожный, — второй такой же уехал бы в сеть со своим
    предохранителем и со своей квотой."""
    assert registry.people_for(Kind.BOOK) is registry.google_books


async def test_books_still_have_no_ratings(registry):
    """Половина прежнего сторожа, которая осталась правдой: оценок у книг нет и
    не предвидится — Goodreads закрыл выдачу ключей в 2020, у LiveLib
    публичного API нет."""
    assert registry.rating_sources(Kind.BOOK) == []


async def test_only_books_have_a_spare_source_of_covers(registry):
    """Запасной источник обложек есть у книг и больше ни у кого.

    Тождеством, как и у остальных полей маршрута: клиент обязан быть тот же
    самый, что поднят сборкой. Проверка идёт по **боевому** реестру, а не по
    двойнику из `tests/fakes.py`: тот знает то же правило своим литералом, и
    разъехаться они могли молча. Сними `covers` у книг — запасная обложка не
    искалась бы никогда; отдай его музыке — Deezer погнал бы альбомы в FantLab,
    и оба раза весь набор оставался бы зелёным.

    Остальные перебираются по самому перечислению, а не списком: списком
    шестой тип с запасным источником остался бы незамеченным."""
    assert registry.covers_for(Kind.BOOK) is registry.fantlab
    for kind in set(Kind) - {Kind.BOOK}:
        assert registry.covers_for(kind) is None, kind


async def test_albums_are_searched_at_deezer(registry):
    """Тождеством, а не типом: клиент обязан быть тот же самый, что поднят
    сборкой, — второй такой же уехал бы в сеть со своим предохранителем.

    Ту же ловушку сторожит и вторая половина: реестр был написан как «игра или
    всё остальное», и альбом уехал бы в киношную ветку молча — поиск вернул бы
    фильмы, обогащение пошло бы за оценками в MDBList, OMDb и Кинопоиск по
    несуществующему `imdb_id`, и отказа не было бы ни одного."""
    assert registry.catalog_for(Kind.MUSIC) == [registry.deezer]
    assert registry.people_for(Kind.MUSIC) is registry.deezer


async def test_music_asks_nobody_for_ratings(registry):
    """Оценок у музыки нет и не предвидится: своей у Deezer нет вовсе, а
    агрегатора альбомов проект не заводит."""
    assert registry.rating_sources(Kind.MUSIC) == []


async def test_every_kind_has_a_row_in_the_table(registry):
    """Умолчания у маршрутов нет намеренно: шестой тип, добавленный без строки,
    обязан упасть на месте, а не достаться TMDB. Проверяется следствием — тем,
    что ни один из объявленных типов на этом не падает."""
    for kind in Kind:
        registry.catalog_for(kind)
        registry.people_for(kind)
        registry.rating_sources(kind)


async def test_a_kind_outside_the_table_is_refused_on_the_spot(registry):
    """Обратная половина предыдущего: без неё «умолчания нет» не наблюдается
    ничем — таблица, покрывающая все типы, зелена и с `.get(kind, [self.tmdb])`
    внутри."""
    with pytest.raises(KeyError):
        registry.catalog_for("новый-тип")


async def test_every_catalog_client_takes_the_same_arguments(registry):
    """Ради этого реестр и существует: сервис зовёт их одинаково.

    Перебор идёт по всему перечислению, а не по списку типов: сегодня каталог
    есть у всех пяти, но список типов отставал бы от перечисления молча, а
    перебор — нет."""
    for kind in Kind:
        for client in registry.catalog_for(kind):
            assert list(inspect.signature(client.search).parameters) == [
                "query",
                "kind",
                "offset",
            ], type(client)
            assert list(inspect.signature(client.card).parameters) == [
                "source_id",
                "kind",
            ], type(client)


@pytest.mark.parametrize("name", CATALOG_OWNERS)
async def test_each_catalog_client_sits_on_the_connection_of_its_own_name(registry, name):
    """Привязка «имя соединения — клиент» проверяется следствием, а не чтением
    `client.name`: имя в отказе клиенты подставляют литералом, поэтому
    перепутанные местами `http("steam")` и `http("gog")` в сборке молчали бы и
    там, и в сравнении набора имён.

    Взводим предохранитель на соединении с этим именем и спрашиваем каждого из
    четырёх: замолчать обязан ровно один, и это должен быть тот, чьё имя мы
    взвели. Обменяй соединения — замолчит не тот, и тест покраснеет."""
    clients = {owner: getattr(registry, owner) for owner in CATALOG_OWNERS}
    for connection in registry.connections:
        if connection.name == name:
            connection.breaker.trip(timedelta(hours=1))

    silent = set()
    for owner, client in clients.items():
        result = await client.search("что угодно", KIND_OF[owner])
        if isinstance(result, Refusal) and result.detail == "предохранитель взведён":
            silent.add(owner)

    assert silent == {name}


async def test_the_paging_flag_matches_what_the_client_asks():
    """Признак `PAGES` читает сервис поиска, и соврать он может молча в обе
    стороны: ложный у листающего выключает догрузку насовсем, истинный у
    нелистающего заставляет спрашивать вторую порцию, которой не бывает, — и
    тратит запрос из суточной тысячи на каждый поиск.

    Наблюдается не самим признаком, а тем, что клиент делает: запрос со
    смещением сравнивается с запросом без него. Разошлись — клиент листает,
    совпали — второй порции у него нет. Так подмена `True` на `False` перестаёт
    быть невидимой: объявление и поведение сверяются друг с другом."""
    transport, seen = counting(SILENT)
    registry = build_sources(
        load_config({"TMDB_API_KEY": "k"}, base_dir=Path(".")),
        transport=transport,
    )
    try:
        for kind in Kind:
            for client in registry.catalog_for(kind):
                asked = []
                for offset in (0, SEARCH_SIZE):
                    seen.clear()
                    await client.search("дюна", kind, offset)
                    asked.append([str(one.url) for one in seen])
                assert (asked[0] != asked[1]) is client.PAGES, client.name
    finally:
        await registry.aclose()


async def test_every_rating_client_takes_the_same_arguments(registry):
    for client in registry.rating_sources(Kind.MOVIE):
        assert list(inspect.signature(client.ratings).parameters) == [
            "imdb_id",
            "kind",
        ], type(client)
        assert isinstance(client.name, str) and client.name, type(client)


async def test_every_source_has_its_own_breaker(registry):
    """Иначе исчерпанная квота OMDB выключила бы и TMDB."""
    breakers = [one.breaker for one in registry.connections]

    # Оба зеркала Кинопоиска заведены под одним именем: наружу источник один, и
    # в `Refusal.source` человек должен увидеть «kinopoisk», а не имя зеркала.
    assert sorted(one.name for one in registry.connections) == [
        "deezer", "fantlab", "gog", "google_books", "kinopoisk", "kinopoisk",
        "mdblist", "old_games", "omdb", "steam", "tmdb",
    ]
    assert len(breakers) == len({id(one) for one in breakers})
    # Десять источников, но соединений одиннадцать: у Кинопоиска два зеркала.
    # Десятый — FantLab: карточек он не отдаёт, только обложки, а предохранитель
    # ему нужен свой, как и всем.
    assert len(breakers) == 11


async def test_a_tripped_breaker_leaves_the_others_alone(registry):
    """Проверяем следствие, а не пересчитываем объекты: выключенный OMDB не
    должен мешать TMDB отвечать."""
    for one in registry.connections:
        if one.name == "omdb":
            one.breaker.trip(timedelta(hours=1))

    answer = await registry.tmdb.search("Интерстеллар", Kind.MOVIE)
    refused = await registry.omdb.ratings("tt0816692", Kind.MOVIE)

    assert isinstance(answer, Found)
    assert isinstance(refused, Refusal)


def watching_keys() -> tuple[httpx.MockTransport, list]:
    """Транспорт, у которого основное зеркало Кинопоиска отказывает, и список
    ушедших запросов.

    Список ведёт общий `counting`: развилка здесь по хосту, и вложенному
    обработчику список не нужен."""
    def handler(request: httpx.Request) -> httpx.Response:
        # Основное зеркало отказывает, чтобы дошла очередь до запасного.
        if request.url.host == "api.poiskkino.dev":
            return httpx.Response(403, json={"statusCode": 403})
        return httpx.Response(200, json={})

    return counting(httpx.MockTransport(handler))


async def test_the_spare_key_of_google_books_reaches_the_wire_too():
    """Ключей у Google два, и второй уезжает клиенту тем же путём, что первый.

    Проверяется на боевой сборке: сторож настроек держит левое звено (переменная
    окружения → поле), сторож клиента — правое (поле → провод), а середину —
    `config.google_books_keys` в `sources/build.py` — не держал никто. Срежь там
    набор до первого ключа, и запасной перестал бы существовать: книги умирали
    бы на сутки при полном наборе зелёных тестов, ровно в тот день, ради
    которого второй ключ и вписан.

    Первый ключ отвечает исчерпанной квотой — иначе до второго очередь не
    дойдёт вовсе."""
    transport, seen = keys_of_google("google-books-key")
    registry = build_sources(keyed(), transport=transport)

    answer = await registry.google_books.search("дюна", Kind.BOOK)

    assert isinstance(answer, Found), "запасной ключ до провода не доехал"
    assert keys_of(seen) == ["google-books-key", "google-books-spare"]


async def test_every_key_from_the_settings_reaches_its_own_source():
    """Ключ, не доехавший до клиента, виден только отказом источника в бою — и
    выглядит он как чужая поломка, а не как наша опечатка в сборке.

    Ключ сверяется с хостом, а не ищется в общем списке: MDBList и OMDB шлют
    его под одним именем `apikey`, оба зеркала Кинопоиска — одним заголовком, и
    перестановка их местами в общем списке не видна вовсе.

    Google Books шлёт свой третьим именем, `key`. Без него подмена ключа в
    сборке — `config.google_books_key` на любой соседний — оставляла бы весь
    набор зелёным, а в бою каждая книга получала бы «ключ не принят»: сторож
    настроек держит только левое звено, от переменной окружения до поля."""
    transport, seen = watching_keys()
    registry = build_sources(keyed(), transport=transport)

    await registry.tmdb.search("что угодно", Kind.MOVIE)
    await registry.google_books.search("что угодно", Kind.BOOK)
    await registry.mdblist.ratings("tt0816692", Kind.MOVIE)
    await registry.omdb.ratings("tt0816692", Kind.MOVIE)
    await registry.kinopoisk.ratings("tt0816692", Kind.MOVIE)

    assert {one.url.host: key_of(one) for one in seen} == {
        "api.themoviedb.org": "tmdb-key",
        "www.googleapis.com": "google-books-key",
        "api.mdblist.com": "mdblist-key",
        "www.omdbapi.com": "omdb-key",
        "api.poiskkino.dev": "poiskkino-key",
        "kinopoiskapiunofficial.tech": "unofficial-key",
    }


async def test_a_card_goes_back_to_the_client_it_came_from(registry):
    """Все подставные клиенты в тестах сервисов аргумент игнорируют — если
    словарь тут перепутан, заметить это можно только здесь.

    Перебором по перечислению, а не списком из четырёх строк: седьмой источник
    в списке забыли бы, и карточка книги уходила бы обновляться в никуда."""
    for source in Source:
        if source is Source.MANUAL:
            continue
        assert registry.client_for(source) is getattr(registry, str(source)), source


async def test_a_manual_card_has_no_client(registry):
    """Она ниоткуда не приезжала — загружать нечего."""
    assert registry.client_for(Source.MANUAL) is None


async def test_closing_closes_every_connection():
    """Незакрытый пул уходит вместе с приложением висящими сокетами.

    Реестр тут свой, а не из фикстуры: закрытие и есть предмет проверки, и
    звать его должен сам тест."""
    registry = sources()
    await registry.aclose()

    for one in registry.connections:
        try:
            await one.get("https://example.invalid/")
        except RuntimeError:
            continue
        raise AssertionError(f"соединение {one.name} осталось открытым")


@pytest.mark.parametrize("owner", [*CATALOG_OWNERS, "mdblist", "omdb"])
async def test_a_client_signs_refusals_with_the_name_it_calls_itself(owner):
    """`name` уходит наружу единственным путём: сорвись у клиента корутина, имя
    отказу подставит не он сам, а поймавший его `answered`. Разойдись оно с
    литералом, которым клиент подписывает собственные отказы, — и человек увидит
    в логе два разных источника вместо одного, а искать пойдёт не тот ключ.
    Ровно этим однажды обернулось общее `imdb` у двух оценочных клиентов.

    Отказ нужен именно собственный, собранный литералом. Мёртвая сеть для этого
    не годится: её отказ подписывает `SourceHttp` своим же именем, и сравнение
    вышло бы тавтологией. Поэтому каталожным даём пустое тело под кодом 200 —
    разбор его не переживает, — а оценочным код 500, которого у них не описано:
    и то, и другое клиент подписывает сам.

    Кинопоиска в пятёрке нет намеренно: имя и подписи отказов обоих его зеркал
    берутся из одной константы `SOURCE`, и сверка вышла бы той самой
    тавтологией."""
    catalog = owner in CATALOG_OWNERS
    registry = build_sources(
        keyed(), transport=SILENT if catalog else responding(500)
    )
    client = getattr(registry, owner)

    if catalog:
        result = await client.card("1", Kind.MOVIE if owner == "tmdb" else Kind.GAME)
    else:
        result = await client.ratings("tt0816692", Kind.MOVIE)

    assert isinstance(result, Refusal), f"{owner}: этот ответ обязан отказать"
    assert result.source == client.name

