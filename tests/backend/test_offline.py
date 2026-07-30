"""Главное обещание приложения: без сети работает всё, кроме поиска чужого."""

import httpx
import pytest

from backend.app import build_backend
from backend.config import load_config
from backend.model import (
    CompanyRole,
    Credit,
    Filters,
    Kind,
    PersonRole,
    Source,
    SourceCard,
    new_manual_item,
)
from backend.sources.errors import Reason, Refusal
from backend.storage.session import create_engine
from backend.storage.tables import metadata
from tests.conftest import MOMENT, RATED, WANTED, an_item


def unplugged(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("сети нет", request=request)


def mine(title: str, **fields):
    """`new_manual_item` не подставляет `synced_at` сама — поле у `Item`
    обязательное, и передавать его должен вызывающий."""
    return new_manual_item(Kind.MOVIE, title, synced_at=MOMENT, **fields)


async def assemble(tmp_path):
    engine = create_engine(tmp_path / "library.db")
    async with engine.begin() as connection:
        await connection.run_sync(metadata.create_all)
    await engine.dispose()

    config = load_config({"DATA_DIR": str(tmp_path)}, base_dir=tmp_path)
    return await build_backend(config,
                               transport=httpx.MockTransport(unplugged))


@pytest.fixture
async def offline(tmp_path):
    backend = await assemble(tmp_path)
    yield backend
    await backend.aclose()


async def test_a_card_is_made_by_hand(offline):
    item_id = await offline.library.create(mine("Домашнее видео", year=2019))

    stored = await offline.library.get(item_id)
    assert stored.title == "Домашнее видео"


async def test_a_score_is_given_and_kept(offline):
    item_id = await offline.library.create(mine("Своё"))

    await offline.ratings.set_score(item_id, 9.0, now=MOMENT)

    assert (await offline.ratings.get(item_id)).score == 9.0


async def test_the_local_search_still_finds(offline):
    await offline.library.create(mine("Домашнее видео"))

    found = await offline.search.local(Kind.MOVIE, "домашнее")

    assert [view.title for view in found] == ["Домашнее видео"]


async def test_the_external_search_reports_the_reason(offline):
    """Не пустой экран и не ошибка: выдача остаётся локальной, плашка снизу
    говорит, что внешняя база недоступна.

    Причина проверяется отдельно: плашка говорит человеку разное при обрыве сети
    и при исчерпанной квоте, и спутать их нельзя."""
    result = await offline.search.external(Kind.MOVIE, "интерстеллар")

    assert result.views == ()
    assert [r.reason for r in result.refusals] == [Reason.NETWORK]


async def test_the_feed_works(offline):
    item_id = await offline.library.create(mine("Своё"))
    await offline.ratings.set_score(item_id, 8.0, now=MOMENT)

    page = await offline.feed.page(RATED)

    assert [view.title for view in page] == ["Своё"]


async def test_the_histogram_is_built(offline):
    item_id = await offline.library.create(mine("Своё"))
    await offline.ratings.set_score(item_id, 8.0, now=MOMENT)

    histogram = await offline.feed.histogram(Kind.MOVIE, Filters())

    assert next(b.count for b in histogram.buckets if b.score == 8) == 1
    assert histogram.average == 8.0


async def test_the_wishlist_works(offline):
    item_id = await offline.library.create(mine("Потом"))

    await offline.wishlist.add(item_id, now=MOMENT)
    page = await offline.feed.page(WANTED)

    assert [view.title for view in page] == ["Потом"]


async def test_tags_are_edited(offline):
    item_id = await offline.library.create(mine("Своё"))
    tag_id = await offline.tags.create(Kind.MOVIE, "пересмотреть")

    await offline.tags.assign(item_id, tag_id)

    assert [name for _, name in await offline.tags.tags_of(item_id)] == [
        "пересмотреть"
    ]


async def test_a_card_is_deleted_with_everything_of_mine(offline):
    item_id = await offline.library.create(mine("Своё"))
    await offline.ratings.set_score(item_id, 8.0, now=MOMENT)

    await offline.library.delete(item_id, offline.posters.store)

    assert await offline.library.get(item_id) is None
    assert await offline.ratings.get(item_id) is None


async def test_a_single_card_can_be_redrawn(offline):
    """После загрузки кандидата и после простановки оценки ленте нужно
    перерисовать одну карточку. Спросить её больше негде: `page` умеет только
    страницу раздела, `local` — только по строке запроса."""
    item_id = await offline.library.create(mine("Своё"))
    await offline.ratings.set_score(item_id, 7.0, now=MOMENT)

    views = await offline.views.views_for([item_id])

    assert views[item_id].rating.score == 7.0


async def test_the_cast_of_a_hand_made_card_is_kept(offline):
    """Люди и студии — два разных репозитория с одинаковым устройством, и в
    сборке их легко поменять местами. Тогда актёр уехал бы в студии, а тесты
    репозиториев этого не увидели бы: там их собирают по отдельности."""
    item_id = await offline.library.create(mine("Своё"))
    actor = await offline.people.create_manual("Мэттью Макконахи")
    studio = await offline.companies.create_manual("Syncopy")
    await offline.people.attach(item_id, actor, PersonRole.ACTOR, 0)
    await offline.companies.attach(item_id, studio, CompanyRole.PUBLISHER)

    view = (await offline.views.views_for([item_id]))[item_id]

    assert [credit.name for credit in view.people] == ["Мэттью Макконахи"]
    assert [credit.name for credit in view.companies] == ["Syncopy"]


async def test_a_hand_made_card_gets_linked_to_a_source(offline):
    """Привязка собрана на тех же репозиториях, что и писатель, и перепутать в
    ней людей со студиями так же легко — а тесты самой привязки собирают её сами
    и подмены в сборке не видят.

    Сеть тут не нужна: карточку источника подаём готовой, как её подал бы путь по
    ссылке."""
    item_id = await offline.library.create(mine("Своё"))
    incoming = SourceCard(
        item=an_item("157336", "Интерстеллар", year=2014),
        people=(Credit("Кристофер Нолан", PersonRole.DIRECTOR),),
    )

    await offline.linker.link(item_id, incoming, now=MOMENT)

    view = (await offline.views.views_for([item_id]))[item_id]
    assert (view.year, view.source_id) == (2014, "157336")
    assert [credit.name for credit in view.people] == ["Кристофер Нолан"]
    assert view.companies == ()


async def test_a_cover_from_the_network_is_a_refusal_and_not_a_hang(offline):
    """Транспорт доезжает и до обложек: без него сервис постеров поднял бы
    настоящий клиент и полез в сеть из теста."""
    result = await offline.posters.poster_for(
        None, Source.TMDB, "https://example.com/p.jpg", MOMENT
    )

    assert isinstance(result, Refusal)
    assert result.reason is Reason.NETWORK


async def test_the_data_folder_is_made_if_it_is_not_there(tmp_path):
    """Первый запуск на чистой машине: папки данных ещё нет. Хранилище постеров
    само её не создаёт — sqlite просто не откроется."""
    fresh = tmp_path / "которой-нет"
    config = load_config({"DATA_DIR": str(fresh)}, base_dir=tmp_path)

    backend = await build_backend(config,
                                  transport=httpx.MockTransport(unplugged))
    await backend.aclose()

    assert (fresh / "posters.db").exists()


async def test_the_enrichment_asks_nobody_without_the_network(offline):
    """Третий круг без сети не пишет в базу ничего: отказ — не «у источника
    нет», и через неделю пустая строка не должна выдать себя за ответ."""
    item_id = await offline.library.create(mine("Своё"))

    ratings = await offline.enricher.enrich(item_id, Kind.MOVIE)

    assert ratings == []


async def test_everything_closes_and_lets_go(tmp_path):
    """Пустой `aclose` прошёл бы проверку «файл существует» — проверяем, что
    закрыты все трое: соединения источников, хранилище постеров и движок базы.

    Движок проверяется занятым пулом: после запроса соединение возвращается в
    пул, и `dispose` его оттуда убирает. На пустом пуле ноль был бы и без
    закрытия."""
    backend = await assemble(tmp_path)
    await backend.library.get(1)
    assert backend._engine.pool.checkedin() == 1

    await backend.aclose()

    assert backend._engine.pool.checkedin() == 0
    # PosterStore.close() закрывает соединение, и обращение после этого падает.
    # Если он окажется способен открыться заново, тест покраснеет — и это
    # правильный сигнал: закрытие тогда не закрытие.
    with pytest.raises(Exception):
        await backend.posters.store.get(1)
    for connection in backend.sources.connections:
        with pytest.raises(RuntimeError):
            await connection.get("https://example.invalid/")


async def test_closing_twice_is_quiet(tmp_path):
    """Фикстура закрывает бэкенд после теста, и тест может закрыть его сам."""
    backend = await assemble(tmp_path)

    await backend.aclose()
    await backend.aclose()
