"""Обложка видимой карточки: лежащая отдаётся, недостающая скачивается."""

import pytest

from backend.model import Kind, Refusal, Source
from tests.conftest import (
    MOMENT,
    PICTURE,
    UNSHAPED,
    capture,
    poster_service,
    responding,
    size_of,
)

# Вторая картинка нужна, чтобы отличить «отдали лежащее» от «скачали заново»:
# с одинаковыми байтами эти два случая неразличимы. Подпись JPEG, а не PNG.
STORED = bytes.fromhex("ffd8ffe000104a46") + b"0" * 64


@pytest.fixture
async def covers(posters):
    """Сервис обложек и список ушедших за картинкой запросов: на нём стоит
    проверка того, что лежащее в хранилище сети не стоит."""
    transport, seen = capture(content=PICTURE)
    return poster_service(posters, transport), seen


async def test_a_stored_cover_comes_back_without_the_network(covers):
    service, asked = covers
    await service._store.put(1, STORED, MOMENT)

    data = await service.poster_for(1, Source.TMDB, "https://e.com/p.jpg", MOMENT,
                                    Kind.MOVIE)

    assert data == STORED
    assert asked == []


async def test_empty_bytes_in_the_store_are_still_an_answer(covers):
    """«Нет строки» и «строка пустая» — разные вещи, как у оценок агрегаторов.
    Своим путём пустые байты в хранилище не попадут: скачанное проверяется по
    подписи формата, залитое руками — обрезкой. А вот из старой версии или из
    битого файла — попадут, и тогда лента полезет в сеть на каждый показ."""
    service, asked = covers
    await service._store.put(1, b"", MOMENT)

    data = await service.poster_for(1, Source.TMDB, "https://e.com/p.jpg", MOMENT,
                                    Kind.MOVIE)

    assert data == b""
    assert asked == []


async def test_a_missing_cover_is_downloaded_and_kept(covers):
    service, asked = covers

    data = await service.poster_for(1, Source.TMDB, "https://e.com/p.jpg", MOMENT,
                                    Kind.MOVIE)

    assert data == PICTURE
    assert await service._store.get(1) == PICTURE
    assert [str(one.url) for one in asked] == ["https://e.com/p.jpg"]


async def test_a_candidate_gets_its_cover_but_nothing_is_stored(covers):
    """У кандидата строки в базе ещё нет — класть обложку некуда. Сохранит её
    загрузчик вместе с карточкой."""
    service, _ = covers

    data = await service.poster_for(None, Source.TMDB, "https://e.com/p.jpg",
                                    MOMENT, Kind.MOVIE)

    assert data == PICTURE
    assert not await service._store.has(1)


async def test_a_card_without_a_cover_asks_nobody(covers):
    service, asked = covers

    assert await service.poster_for(1, Source.TMDB, "", MOMENT,
                                    Kind.MOVIE) is None
    assert asked == []


async def test_a_shown_album_keeps_its_square_and_the_store_gets_it(posters):
    """Показ карточки — главный путь обложки: по нему она и приезжает в ленту,
    и **ложится в хранилище**. Тип обязан доехать до обрезки и здесь, иначе
    альбом сохранился бы афишей с обрезанными боками — навсегда, потому что
    лежащее в хранилище больше не перекачивается.

    Оба следствия сразу: отданное и сохранённое."""
    service = poster_service(posters, responding(content=UNSHAPED))
    try:
        data = await service.poster_for(1, Source.DEEZER,
                                        "https://cdn.deezer.com/w.jpg", MOMENT,
                                        Kind.MUSIC)
        stored = await service._store.get(1)
    finally:
        await service.aclose()

    assert size_of(data)[0] == size_of(data)[1], "отдали афишу"
    assert size_of(stored)[0] == size_of(stored)[1], "в хранилище легла афиша"


async def test_a_shown_candidate_keeps_its_square_too(posters):
    """У кандидата номера нет, класть обложку некуда — но показывается она тем
    же путём, и тип по нему едет свой. Ветка отдельная, и подмена типа в ней
    молчала бы, даже если соседняя сторожится."""
    service = poster_service(posters, responding(content=UNSHAPED))
    try:
        data = await service.poster_for(None, Source.DEEZER,
                                        "https://cdn.deezer.com/w.jpg", MOMENT,
                                        Kind.MUSIC)
    finally:
        await service.aclose()

    assert size_of(data)[0] == size_of(data)[1], "кандидату отдали афишу"


async def test_a_refusal_is_returned_and_nothing_is_stored(posters):
    transport, _ = capture(content=PICTURE, status=500)
    service = poster_service(posters, transport)

    result = await service.poster_for(1, Source.TMDB, "https://e.com/p.jpg",
                                      MOMENT, Kind.MOVIE)

    assert isinstance(result, Refusal)
    assert await service._store.get(1) is None


async def test_the_second_show_of_the_same_card_costs_nothing(covers):
    """Скачанное сохраняется тут же — иначе каждая прокрутка ленты качала бы
    те же обложки заново."""
    service, asked = covers

    await service.poster_for(1, Source.TMDB, "https://e.com/p.jpg", MOMENT,
                                    Kind.MOVIE)
    await service.poster_for(1, Source.TMDB, "https://e.com/p.jpg", MOMENT,
                                    Kind.MOVIE)

    assert len(asked) == 1
