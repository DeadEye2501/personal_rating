"""`PROVIDES` против того, что клиент действительно разбирает.

Список нужен не сам себе: по нему пишется пустое значение — «спрашивали, у
источника нет» — и по нему же считается, сколько ответов ждать. Сверять его с
таким же списком в тесте бессмысленно: разойтись он может не с ожидаемым, а с
разбором, и тогда приложение либо потеряет привезённое даром, либо на неделю
соврёт «у него нет» про источник, которого никто не спрашивал."""

import pytest

from backend.model import Found, Kind
from backend.sources.http import SourceHttp
from backend.sources.ratings.kinopoisk.client import KinopoiskClient
from backend.sources.ratings.kinopoisk.poiskkino import PoiskkinoClient
from backend.sources.ratings.kinopoisk.unofficial import UnofficialClient
from backend.sources.ratings.mdblist.client import MdbListClient
from backend.sources.ratings.omdb.client import OmdbClient


def mdblist(transport) -> MdbListClient:
    return MdbListClient(SourceHttp("mdblist", transport=transport), api_key="k")


def omdb(transport) -> OmdbClient:
    return OmdbClient(SourceHttp("omdb", transport=transport), api_key="k")


def kinopoisk(transport) -> KinopoiskClient:
    """Оба зеркала на одном транспорте: разбирает ответ то, до которого дошло
    дело, а наружу они неразличимы."""
    return KinopoiskClient(
        PoiskkinoClient(SourceHttp("kinopoisk", transport=transport), api_key="k"),
        UnofficialClient(SourceHttp("kinopoisk", transport=transport), api_key="k"),
    )


# Полный записанный ответ каждого источника: на нём видно всё, что он привозит.
FULL_ANSWERS = (
    (mdblist, "mdblist/found.json"),
    (omdb, "omdb/found.json"),
    (kinopoisk, "kinopoisk/poiskkino_found.json"),
)


async def brought_by(build, recorded, replay) -> tuple[set, set]:
    """Что источник привёз на полном ответе и что он про себя объявил."""
    client = build(replay(recorded))
    result = await client.ratings("tt0816692", Kind.MOVIE)
    assert isinstance(result, Found), "полный записанный ответ должен разобраться"
    return {one.source for one in result.value.values}, set(client.PROVIDES)


@pytest.mark.parametrize(("build", "recorded"), FULL_ANSWERS)
async def test_a_client_brings_nothing_it_did_not_declare(build, recorded, replay):
    """Необъявленную оценку `Enricher` выбрасывает с предупреждением — то есть
    молча теряет привезённое даром. Заметить это можно только здесь."""
    brought, declared = await brought_by(build, recorded, replay)

    assert not brought - declared, f"{brought - declared} привезено, но не объявлено"


@pytest.mark.parametrize(("build", "recorded"), FULL_ANSWERS)
async def test_a_client_declares_nothing_it_cannot_bring(build, recorded, replay):
    """Обратная сторона, и она опаснее: лишнее в `PROVIDES` — это право записать
    «у него нет». Впиши KINOPOISK в список OMDB, и всякий раз, когда ответил
    OMDB, приложение на неделю объявит, что у Кинопоиска нет Интерстеллара, —
    ничего у него не спросив."""
    brought, declared = await brought_by(build, recorded, replay)

    assert not declared - brought, \
        f"{declared - brought} объявлено, а полный ответ его не дал"
