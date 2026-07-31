"""Реестр держится на том, что контракт у всех клиентов один."""

import inspect
from datetime import timedelta
from pathlib import Path

import httpx
import pytest

from backend.config import load_config
from backend.model import Found, Kind, Refusal, Source
from backend.sources.gog.client import GogClient
from backend.sources.ratings.kinopoisk.client import KinopoiskClient
from backend.sources.ratings.mdblist.client import MdbListClient
from backend.sources.ratings.omdb.client import OmdbClient
from backend.sources.build import build_sources
from tests.conftest import responding
from backend.sources.steam.client import SteamClient
from backend.sources.tmdb.client import TmdbClient

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


async def test_games_come_from_two_equal_stores(registry):
    """Заметная часть ретро в Steam не продаётся — магазина два."""
    # Список, а не множество: порядок задаёт, чью выдачу человек увидит первой
    # при равном числе кандидатов, а множество обмен магазинов местами скрывает.
    assert [type(one) for one in registry.catalog_for(Kind.GAME)] == [
        SteamClient,
        GogClient,
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


async def test_every_catalog_client_takes_the_same_arguments(registry):
    """Ради этого реестр и существует: сервис зовёт их одинаково."""
    for kind in (Kind.MOVIE, Kind.SERIES, Kind.GAME):
        for client in registry.catalog_for(kind):
            assert list(inspect.signature(client.search).parameters) == [
                "query",
                "kind",
            ], type(client)
            assert list(inspect.signature(client.card).parameters) == [
                "source_id",
                "kind",
            ], type(client)


@pytest.mark.parametrize("name", ["tmdb", "steam", "gog"])
async def test_each_catalog_client_sits_on_the_connection_of_its_own_name(registry, name):
    """Привязка «имя соединения — клиент» проверяется следствием, а не чтением
    `client.name`: имя в отказе клиенты подставляют литералом, поэтому
    перепутанные местами `http("steam")` и `http("gog")` в сборке молчали бы и
    там, и в сравнении набора имён.

    Взводим предохранитель на соединении с этим именем и спрашиваем каждого из
    трёх: замолчать обязан ровно один, и это должен быть тот, чьё имя мы взвели.
    Обменяй соединения — замолчит не тот, и тест покраснеет."""
    clients = {"tmdb": registry.tmdb, "steam": registry.steam, "gog": registry.gog}
    for connection in registry.connections:
        if connection.name == name:
            connection.breaker.trip(timedelta(hours=1))

    silent = set()
    for owner, client in clients.items():
        result = await client.search("что угодно", Kind.MOVIE
                                    if owner == "tmdb" else Kind.GAME)
        if isinstance(result, Refusal) and result.detail == "предохранитель взведён":
            silent.add(owner)

    assert silent == {name}


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
        "gog", "kinopoisk", "kinopoisk", "mdblist", "omdb", "steam", "tmdb",
    ]
    assert len(breakers) == len({id(one) for one in breakers})
    # Шесть источников, но соединений семь: у Кинопоиска два зеркала.
    assert len(breakers) == 7


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


async def test_every_key_from_the_settings_reaches_its_own_source():
    """Ключ, не доехавший до клиента, виден только отказом источника в бою — и
    выглядит он как чужая поломка, а не как наша опечатка в сборке.

    Ключ сверяется с хостом, а не ищется в общем списке: MDBList и OMDB шлют
    его под одним именем `apikey`, оба зеркала Кинопоиска — одним заголовком, и
    перестановка их местами в общем списке не видна вовсе."""
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen[request.url.host] = (
            request.url.params.get("api_key")
            or request.url.params.get("apikey")
            or request.headers.get("x-api-key")
        )
        # Основное зеркало отказывает, чтобы дошла очередь до запасного.
        if request.url.host == "api.poiskkino.dev":
            return httpx.Response(403, json={"statusCode": 403})
        return httpx.Response(200, json={})

    registry = build_sources(keyed(), transport=httpx.MockTransport(handler))

    await registry.tmdb.search("что угодно", Kind.MOVIE)
    await registry.mdblist.ratings("tt0816692", Kind.MOVIE)
    await registry.omdb.ratings("tt0816692", Kind.MOVIE)
    await registry.kinopoisk.ratings("tt0816692", Kind.MOVIE)

    assert seen == {
        "api.themoviedb.org": "tmdb-key",
        "api.mdblist.com": "mdblist-key",
        "www.omdbapi.com": "omdb-key",
        "api.poiskkino.dev": "poiskkino-key",
        "kinopoiskapiunofficial.tech": "unofficial-key",
    }


async def test_a_card_goes_back_to_the_client_it_came_from(registry):
    """Все подставные клиенты в тестах сервисов аргумент игнорируют — если
    словарь тут перепутан, заметить это можно только здесь."""
    assert registry.client_for(Source.TMDB) is registry.tmdb
    assert registry.client_for(Source.STEAM) is registry.steam
    assert registry.client_for(Source.GOG) is registry.gog


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


CATALOG_OWNERS = ("tmdb", "steam", "gog")


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

