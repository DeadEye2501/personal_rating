from datetime import timedelta

import pytest

from backend.model import Item, Kind, SeriesCounts, Source
from backend.service.loading import REFRESH_TTL, Loader
from backend.sources.errors import Found, Missing, Reason, Refusal
from backend.storage.repository.library import LibraryRepository
from tests.conftest import MOMENT, FakeClient, FakeSources, an_item

LONG_AGO = MOMENT - timedelta(days=40)


class FakeTmdb(FakeClient):
    """Спрашивают у него только сезоны с сериями."""

    async def series_counts(self, source_id: str):
        self.asked.append(source_id)
        return self.outcome


def series(synced_at, seasons=1, episodes=12) -> Item:
    return an_item("83867", "Andor", kind=Kind.SERIES, synced_at=synced_at,
                   seasons_count=seasons, episodes_count=episodes)


@pytest.fixture
async def refresher(sessions):
    """Загрузчик с остановленными часами: срок годности — предмет проверки, и
    зависеть она от настоящего времени не должна."""

    def build(outcome):
        tmdb = FakeTmdb(outcome)
        loader = Loader(library=LibraryRepository(sessions), writer=None,
                        sources=FakeSources(tmdb), posters=None,
                        clock=lambda: MOMENT)
        return loader, tmdb

    return build


async def test_a_stale_series_gets_new_counts(sessions, refresher):
    item_id = await LibraryRepository(sessions).create(series(LONG_AGO))
    loader, _ = refresher(Found(SeriesCounts(seasons=2, episodes=24)))

    await loader.refresh(item_id)

    stored = await LibraryRepository(sessions).get(item_id)
    assert (stored.seasons_count, stored.episodes_count) == (2, 24)


async def test_the_refreshed_card_gets_a_new_moment(sessions, refresher):
    """Иначе следующий показ пойдёт за теми же числами опять."""
    item_id = await LibraryRepository(sessions).create(series(LONG_AGO))
    loader, _ = refresher(Found(SeriesCounts(seasons=2, episodes=24)))

    await loader.refresh(item_id)

    stored = await LibraryRepository(sessions).get(item_id)
    assert stored.synced_at == MOMENT


async def test_a_half_empty_answer_does_not_erase_what_was_known(sessions,
                                                                refresher):
    """Число, которого в ответе нет, не стирает хранимое: сезоны у сериала уже
    были, и неполный ответ — не повод их забыть."""
    item_id = await LibraryRepository(sessions).create(
        series(LONG_AGO, seasons=1, episodes=12)
    )
    loader, _ = refresher(Found(SeriesCounts(seasons=2, episodes=None)))

    await loader.refresh(item_id)

    stored = await LibraryRepository(sessions).get(item_id)
    assert (stored.seasons_count, stored.episodes_count) == (2, 12)


async def test_a_fresh_series_is_not_asked_about(sessions, refresher):
    item_id = await LibraryRepository(sessions).create(series(MOMENT))
    loader, tmdb = refresher(Found(SeriesCounts(seasons=2, episodes=24)))

    await loader.refresh(item_id)

    assert tmdb.asked == []


async def test_the_edge_of_the_term_is_not_stale_yet(sessions, refresher):
    """Границу щупаем самой константой: с литералом тест сломался бы от смены
    политики, а не от поломки.

    Сама величина при этом тоже закреплена — иначе срок можно урезать вдвое, и
    все проверки, отмеренные от него же, останутся зелёными."""
    assert REFRESH_TTL == timedelta(days=30)
    item_id = await LibraryRepository(sessions).create(
        series(MOMENT - REFRESH_TTL)
    )
    loader, tmdb = refresher(Found(SeriesCounts(seasons=2, episodes=24)))

    await loader.refresh(item_id)

    assert tmdb.asked == []


async def test_a_day_past_the_term_is_stale(sessions, refresher):
    item_id = await LibraryRepository(sessions).create(
        series(MOMENT - REFRESH_TTL - timedelta(days=1))
    )
    loader, tmdb = refresher(Found(SeriesCounts(seasons=2, episodes=24)))

    await loader.refresh(item_id)

    assert tmdb.asked == ["83867"]


async def test_a_film_is_never_re_asked(sessions, refresher):
    """У фильма меняться нечему: длительность после выхода не растёт."""
    item_id = await LibraryRepository(sessions).create(
        Item(id=0, kind=Kind.MOVIE, source=Source.TMDB, source_id="157336",
             title="Интерстеллар", synced_at=LONG_AGO)
    )
    loader, tmdb = refresher(Found(SeriesCounts(seasons=2, episodes=24)))

    await loader.refresh(item_id)

    assert tmdb.asked == []


async def test_a_manual_card_is_never_re_asked(sessions, refresher):
    """Перезапрашивать нечего: она ниоткуда не приезжала."""
    item_id = await LibraryRepository(sessions).create(
        Item(id=0, kind=Kind.SERIES, source=Source.MANUAL,
             source_id="9f1c-своя", title="Своё", synced_at=LONG_AGO)
    )
    loader, tmdb = refresher(Found(SeriesCounts(seasons=2, episodes=24)))

    await loader.refresh(item_id)

    assert tmdb.asked == []


async def test_a_refusal_leaves_the_card_as_it_was(sessions, refresher):
    item_id = await LibraryRepository(sessions).create(series(LONG_AGO))
    loader, _ = refresher(Refusal(source="tmdb", reason=Reason.NETWORK))

    await loader.refresh(item_id)

    stored = await LibraryRepository(sessions).get(item_id)
    assert (stored.seasons_count, stored.synced_at) == (1, LONG_AGO)


async def test_a_broken_client_leaves_the_card_as_it_was(sessions, refresher,
                                                        caplog):
    """Сорвавшийся клиент — тот же отказ: карточка остаётся прежней, а наружу
    исключение не летит."""
    item_id = await LibraryRepository(sessions).create(series(LONG_AGO))
    loader, tmdb = refresher(None)

    async def broken(source_id):
        raise RuntimeError("разбор не удался")

    tmdb.series_counts = broken
    with caplog.at_level("ERROR"):
        await loader.refresh(item_id)

    stored = await LibraryRepository(sessions).get(item_id)
    assert (stored.seasons_count, stored.synced_at) == (1, LONG_AGO)


async def test_a_vanished_series_is_logged_and_kept(sessions, refresher, caplog):
    """Карточка твоя: из TMDB пропала — у тебя осталась."""
    item_id = await LibraryRepository(sessions).create(series(LONG_AGO))
    loader, _ = refresher(Missing())

    with caplog.at_level("WARNING"):
        await loader.refresh(item_id)

    stored = await LibraryRepository(sessions).get(item_id)
    assert (stored.seasons_count, stored.synced_at) == (1, LONG_AGO)
    assert "83867" in caplog.text


async def test_an_unknown_card_is_simply_skipped(sessions, refresher):
    loader, tmdb = refresher(Found(SeriesCounts(seasons=2, episodes=24)))

    await loader.refresh(999999)

    assert tmdb.asked == []
