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
from backend.sources.steam.client import SteamClient
from backend.sources.tmdb.client import TmdbClient

SILENT = httpx.MockTransport(lambda request: httpx.Response(200, json={}))


def sources():
    return build_sources(
        load_config({"TMDB_API_KEY": "k"}, base_dir=Path(".")), transport=SILENT
    )


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


async def test_films_and_series_come_from_tmdb():
    registry = sources()

    for kind in (Kind.MOVIE, Kind.SERIES):
        assert [type(one) for one in registry.catalog_for(kind)] == [TmdbClient], kind

    await registry.aclose()


async def test_games_come_from_two_equal_stores():
    """Заметная часть ретро в Steam не продаётся — магазина два."""
    registry = sources()

    assert {type(one) for one in registry.catalog_for(Kind.GAME)} == {
        SteamClient,
        GogClient,
    }

    await registry.aclose()


async def test_films_ask_three_aggregators():
    registry = sources()

    assert {type(one) for one in registry.rating_sources(Kind.MOVIE)} == {
        MdbListClient,
        OmdbClient,
        KinopoiskClient,
    }

    await registry.aclose()


@pytest.mark.parametrize("kind", [Kind.MOVIE, Kind.SERIES])
async def test_films_and_series_ask_the_same_three(kind):
    """Список задан явно, а не сравнением двух вызовов между собой: у кино и
    сериалов в реестре один и тот же `return`, и такое сравнение сходилось бы при
    любой реализации, включая пустую."""
    registry = sources()

    assert [type(one) for one in registry.rating_sources(kind)] == [
        MdbListClient, OmdbClient, KinopoiskClient
    ]

    await registry.aclose()


async def test_games_ask_nobody_for_ratings():
    """Оценки критиков у игр приходят даром: Metascore от Steam, своя от GOG.
    Отдельного источника нет и не нужно — ни ключа, ни запроса, ни квоты."""
    registry = sources()

    assert registry.rating_sources(Kind.GAME) == []

    await registry.aclose()


async def test_every_catalog_client_takes_the_same_arguments():
    """Ради этого реестр и существует: сервис зовёт их одинаково."""
    registry = sources()

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
            # Вторая половина контракта: сервисы зовут `client.name`, собирая
            # отказ. Снятие свойства оставило бы реестр зелёным, а `answered(...)`
            # упало бы на `AttributeError` уже в сервисе.
            assert isinstance(client.name, str) and client.name, type(client)

    await registry.aclose()


async def test_every_rating_client_takes_the_same_arguments():
    registry = sources()

    for client in registry.rating_sources(Kind.MOVIE):
        assert list(inspect.signature(client.ratings).parameters) == [
            "imdb_id",
            "kind",
        ], type(client)
        assert isinstance(client.name, str) and client.name, type(client)

    await registry.aclose()


async def test_every_source_has_its_own_breaker():
    """Иначе исчерпанная квота OMDB выключила бы и TMDB."""
    registry = sources()

    breakers = [one.breaker for one in registry.connections]

    # Оба зеркала Кинопоиска заведены под одним именем: наружу источник один, и
    # в `Refusal.source` человек должен увидеть «kinopoisk», а не имя зеркала.
    assert sorted(one.name for one in registry.connections) == [
        "gog", "kinopoisk", "kinopoisk", "mdblist", "omdb", "steam", "tmdb",
    ]
    assert len(breakers) == len({id(one) for one in breakers})
    # Шесть источников, но соединений семь: у Кинопоиска два зеркала.
    assert len(breakers) == 7

    await registry.aclose()


async def test_a_tripped_breaker_leaves_the_others_alone():
    """Проверяем следствие, а не пересчитываем объекты: выключенный OMDB не
    должен мешать TMDB отвечать."""
    registry = sources()
    for one in registry.connections:
        if one.name == "omdb":
            one.breaker.trip(timedelta(hours=1))

    answer = await registry.tmdb.search("Интерстеллар", Kind.MOVIE)
    refused = await registry.omdb.ratings("tt0816692", Kind.MOVIE)
    await registry.aclose()

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
    await registry.aclose()

    assert seen == {
        "api.themoviedb.org": "tmdb-key",
        "api.mdblist.com": "mdblist-key",
        "www.omdbapi.com": "omdb-key",
        "api.poiskkino.dev": "poiskkino-key",
        "kinopoiskapiunofficial.tech": "unofficial-key",
    }


async def test_a_card_goes_back_to_the_client_it_came_from():
    """Все подставные клиенты в тестах сервисов аргумент игнорируют — если
    словарь тут перепутан, заметить это можно только здесь."""
    registry = sources()

    assert registry.client_for(Source.TMDB) is registry.tmdb
    assert registry.client_for(Source.STEAM) is registry.steam
    assert registry.client_for(Source.GOG) is registry.gog

    await registry.aclose()


async def test_a_manual_card_has_no_client():
    """Она ниоткуда не приезжала — загружать нечего."""
    registry = sources()

    assert registry.client_for(Source.MANUAL) is None

    await registry.aclose()


async def test_closing_closes_every_connection():
    """Незакрытый пул уходит вместе с приложением висящими сокетами."""
    registry = sources()

    await registry.aclose()

    for one in registry.connections:
        try:
            await one.get("https://example.invalid/")
        except RuntimeError:
            continue
        raise AssertionError(f"соединение {one.name} осталось открытым")
