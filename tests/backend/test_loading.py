import asyncio
from dataclasses import dataclass

import pytest

from backend.model import (
    CardView,
    Credit,
    Item,
    Kind,
    PersonRole,
    Source,
    SourceCard,
)
from backend.service.cards import CardWriter
from backend.service.loading import Loader
from backend.service.posters import PosterService
from backend.sources.errors import Found, Missing, Reason, Refusal
from backend.storage.repository.library import LibraryRepository
from backend.storage.repository.views import ViewsRepository
from tests.conftest import (
    MOMENT,
    PICTURE,
    FakeClient,
    FakeSources,
    capture,
    card_parts,
)


class FakeCatalog(FakeClient):
    """Спрашивают у него только детальную карточку."""

    async def card(self, source_id: str, kind: Kind):
        self.asked.append((source_id, kind))
        return self.outcome


def candidate(source_id="157336", poster="https://example.com/p.jpg") -> CardView:
    return CardView(kind=Kind.MOVIE, source=Source.TMDB, source_id=source_id,
                    title="Интерстеллар", poster_url=poster)


def source_card(source_id="157336",
                poster="https://example.com/p.jpg") -> SourceCard:
    return SourceCard(
        item=Item(id=0, kind=Kind.MOVIE, source=Source.TMDB,
                  source_id=source_id, title="Интерстеллар", synced_at=MOMENT,
                  runtime=169, poster_url=poster),
        people=(Credit("Кристофер Нолан", PersonRole.DIRECTOR,
                       source=Source.TMDB, source_id="525"),),
    )


@dataclass(frozen=True, slots=True)
class Rig:
    """Загрузчик и всё, за чем в тесте наблюдают: клиент, которому он задаёт
    вопрос, сервис обложек и список ушедших за обложкой запросов."""

    load: Loader
    client: FakeCatalog
    posters: PosterService
    requests: list


@pytest.fixture
async def loader(sessions, posters):
    """Оснастка загрузки. Обложка приходит из подставного транспорта:
    настоящей сети в тестах нет."""

    def build(outcome, poster_status: int = 200) -> Rig:
        transport, asked = capture(content=PICTURE, status=poster_status)
        parts = card_parts(sessions, posters, transport)
        client = FakeCatalog(outcome)
        return Rig(
            load=Loader(library=LibraryRepository(sessions),
                        writer=CardWriter(**parts),
                        sources=FakeSources(client),
                        posters=parts["posters"]),
            client=client,
            posters=parts["posters"],
            requests=asked,
        )

    return build


async def test_a_candidate_becomes_a_card(sessions, loader):
    rig = loader(Found(source_card()))

    item_id = await rig.load.ensure(candidate())

    assert isinstance(item_id, int)
    stored = await LibraryRepository(sessions).get(item_id)
    assert (stored.title, stored.runtime) == ("Интерстеллар", 169)


async def test_the_detail_round_brings_what_the_search_lacked(sessions, loader):
    """У кандидата длительность и состав пустуют, пока не приехал круг 2а."""
    rig = loader(Found(source_card()))

    item_id = await rig.load.ensure(candidate())

    view = (await ViewsRepository(sessions).views_for([item_id]))[item_id]
    assert view.runtime == 169
    assert [c.name for c in view.people] == ["Кристофер Нолан"]


async def test_the_detail_round_is_asked_about_the_right_card(sessions, loader):
    """Номер и тип содержимого едут в источник от кандидата: подмена дала бы
    карточку не того, что человек выбрал."""
    rig = loader(Found(source_card()))

    await rig.load.ensure(candidate("27205"))

    assert rig.client.asked == [("27205", Kind.MOVIE)]


async def test_a_game_is_asked_about_as_a_game(sessions, loader):
    """Тип содержимого едет в источник от кандидата, а не зашит: у Steam и GOG
    он один, но у TMDB от него зависит сама ручка — фильм это или сериал."""
    rig = loader(Found(source_card()))

    await rig.load.ensure(
        CardView(kind=Kind.GAME, source=Source.STEAM, source_id="292030",
                 title="Ведьмак")
    )

    assert rig.client.asked == [("292030", Kind.GAME)]


async def test_the_poster_is_stored_with_the_card(sessions, loader, posters):
    rig = loader(Found(source_card()))

    item_id = await rig.load.ensure(candidate())

    assert await posters.get(item_id) == PICTURE


async def test_a_card_already_in_the_base_is_not_asked_for_again(sessions, loader):
    rig = loader(Found(source_card()))
    existing_id = await LibraryRepository(sessions).create(source_card().item)

    item_id = await rig.load.ensure(candidate())

    assert item_id == existing_id
    assert rig.client.asked == []


async def test_a_view_that_knows_its_identifier_costs_nothing(sessions, loader):
    rig = loader(Found(source_card()))

    result = await rig.load.ensure(CardView(item_id=42, kind=Kind.MOVIE,
                                        source=Source.TMDB, source_id="157336",
                                        title="Интерстеллар"))

    assert result == 42
    assert rig.client.asked == []


async def test_a_refusal_of_the_source_writes_nothing(sessions, loader):
    refusal = Refusal(source="tmdb", reason=Reason.NETWORK)
    rig = loader(refusal)

    result = await rig.load.ensure(candidate())

    assert result is refusal
    assert await LibraryRepository(sessions).find_by_source(
        Source.TMDB, "157336"
    ) is None


async def test_a_vanished_card_is_missing_and_not_a_refusal(sessions, loader):
    rig = loader(Missing())

    assert isinstance(await rig.load.ensure(candidate()), Missing)


async def test_a_broken_client_becomes_a_refusal(sessions, loader, caplog):
    """Сорвалось исключением — наружу оно не летит: у границы потоков второго
    канала доставки нет."""
    rig = loader(Found(source_card()))

    async def broken(source_id, kind):
        raise RuntimeError("разбор не удался")

    rig.client.card = broken
    with caplog.at_level("ERROR"):
        result = await rig.load.ensure(candidate())

    assert isinstance(result, Refusal)
    assert result.reason is Reason.BROKEN
    assert "разбор не удался" in result.detail
    assert await LibraryRepository(sessions).find_by_source(
        Source.TMDB, "157336"
    ) is None


async def test_a_poster_that_did_not_arrive_stops_the_writing(sessions, loader,
                                                              caplog):
    """Не скачалась — карточка не пишется вовсе: повторим при следующем показе.

    Записи об исключении в логе быть не должно: сюда доходит отказ, а не срыв, и
    писателя вообще не зовут. Убери проверку — карточка всё равно не появится в
    базе, но появится в логе, потому что писатель попытается сохранить отказ
    вместо байтов и уберёт за собой уже написанное."""
    rig = loader(Found(source_card()), poster_status=500)

    with caplog.at_level("ERROR"):
        result = await rig.load.ensure(candidate())

    assert isinstance(result, Refusal)
    assert await LibraryRepository(sessions).find_by_source(
        Source.TMDB, "157336"
    ) is None
    assert [r for r in caplog.records
            if r.name.startswith("backend") and r.levelname == "ERROR"] == []


async def test_a_card_without_a_cover_in_the_source_is_still_written(
    sessions, loader, posters
):
    """Обложки нет у самого источника — ждать нечего, он отдал всё, что имел.

    Адреса нет ни у кандидата, ни в детальном ответе: иначе писатель скачал бы
    её сам, вторым запросом, и тест проверял бы не то, что заявляет."""
    rig = loader(Found(source_card(poster="")))

    item_id = await rig.load.ensure(candidate(poster=""))

    assert isinstance(item_id, int)
    assert await posters.get(item_id) is None


async def test_a_cover_absent_from_the_search_but_present_in_the_detail(
    sessions, loader, posters
):
    """Круги 2а и 2б идут разом только тогда, когда адрес пришёл с выдачей. Если
    его там нет, обложка едет вторым запросом уже внутри писателя — правило «не
    скачалась, не пишем» при этом держится."""
    rig = loader(Found(source_card()))

    item_id = await rig.load.ensure(candidate(poster=""))

    assert isinstance(item_id, int)
    assert await posters.get(item_id) == PICTURE


async def test_the_cover_is_fetched_once(sessions, loader):
    """Ради этого круги и идут разом: обложку скачивает загрузчик и передаёт
    писателю готовой. Не передай — писатель полез бы за ней сам, и тот же файл
    приехал бы дважды."""
    rig = loader(Found(source_card()))

    await rig.load.ensure(candidate())

    assert [str(one.url) for one in rig.requests] == ["https://example.com/p.jpg"]


async def test_the_two_rounds_go_together(sessions, loader, monkeypatch):
    """Адрес обложки приходит уже в выдаче — детальный ответ её не ждёт. Пойди
    круги подряд, и обложка началась бы после конца детального ответа."""
    order = []
    rig = loader(Found(source_card()))

    async def slow_card(source_id, kind):
        order.append("карточка началась")
        await asyncio.sleep(0.05)
        order.append("карточка приехала")
        return Found(source_card())

    fetch = rig.posters.fetch

    async def watched(source, url):
        order.append("обложка началась")
        return await fetch(source, url)

    rig.client.card = slow_card
    monkeypatch.setattr(rig.posters, "fetch", watched)

    await rig.load.ensure(candidate())

    assert order.index("обложка началась") < order.index("карточка приехала")


async def test_an_unknown_source_is_a_refusal_and_a_log(sessions, caplog):
    """Ручную карточку загружать неоткуда: каталожного клиента у неё нет. До
    писателя и обложек дело не доходит, поэтому их здесь и нет.

    В сообщении проверяется само действие, а не только источник: клиента
    спрашивают двое, и по логу должно быть видно, кто именно не смог, — иначе
    оба пути называются в нём одинаково. Причина здесь `BROKEN`, а не `NETWORK`:
    ждать нечего, ручная карточка не приедет ни через минуту, ни через час."""
    load = Loader(library=LibraryRepository(sessions), writer=None,
                  sources=FakeSources(), posters=None)

    with caplog.at_level("WARNING"):
        result = await load.ensure(
            CardView(kind=Kind.MOVIE, source=Source.MANUAL, source_id="x",
                     title="Своя")
        )

    assert isinstance(result, Refusal)
    assert (result.source, result.reason) == ("manual", Reason.BROKEN)
    assert "нечем загрузить карточку" in caplog.text
