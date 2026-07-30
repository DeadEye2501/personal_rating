import pytest

from backend.model import Source
from backend.sources.errors import Refusal
from tests.conftest import MOMENT, PICTURE, capture, poster_service

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
    await service.store.put(1, STORED, MOMENT)

    data = await service.poster_for(1, Source.TMDB, "https://e.com/p.jpg", MOMENT)

    assert data == STORED
    assert asked == []


async def test_a_missing_cover_is_downloaded_and_kept(covers):
    service, asked = covers

    data = await service.poster_for(1, Source.TMDB, "https://e.com/p.jpg", MOMENT)

    assert data == PICTURE
    assert await service.store.get(1) == PICTURE
    assert [str(one.url) for one in asked] == ["https://e.com/p.jpg"]


async def test_a_candidate_gets_its_cover_but_nothing_is_stored(covers):
    """У кандидата строки в базе ещё нет — класть обложку некуда. Сохранит её
    загрузчик вместе с карточкой."""
    service, _ = covers

    data = await service.poster_for(None, Source.TMDB, "https://e.com/p.jpg",
                                    MOMENT)

    assert data == PICTURE
    assert not await service.store.has(1)


async def test_a_card_without_a_cover_asks_nobody(covers):
    service, asked = covers

    assert await service.poster_for(1, Source.TMDB, "", MOMENT) is None
    assert asked == []


async def test_a_refusal_is_returned_and_nothing_is_stored(posters):
    transport, _ = capture(content=PICTURE, status=500)
    service = poster_service(posters, transport)

    result = await service.poster_for(1, Source.TMDB, "https://e.com/p.jpg",
                                      MOMENT)

    assert isinstance(result, Refusal)
    assert await service.store.get(1) is None


async def test_the_second_show_of_the_same_card_costs_nothing(covers):
    """Скачанное сохраняется тут же — иначе каждая прокрутка ленты качала бы
    те же обложки заново."""
    service, asked = covers

    await service.poster_for(1, Source.TMDB, "https://e.com/p.jpg", MOMENT)
    await service.poster_for(1, Source.TMDB, "https://e.com/p.jpg", MOMENT)

    assert len(asked) == 1
