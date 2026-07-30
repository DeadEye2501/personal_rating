"""Вставленная ссылка в карточку источника, готовую для привязки."""

import pytest

from backend.model import ExternalLink, Item, Kind, Source, SourceCard
from backend.service.loading import Loader
from backend.sources.errors import Found, Missing, Reason, Refusal
from backend.storage.repository.library import LibraryRepository
from tests.conftest import MOMENT, FakeClient, FakeSources


def source_card(source: Source, source_id: str) -> SourceCard:
    return SourceCard(
        item=Item(id=0, kind=Kind.GAME, source=source, source_id=source_id,
                  title="Arcanum", synced_at=MOMENT)
    )


class FakeCatalog(FakeClient):
    """Спрашивают у него и карточку, и номер по слагу: у GOG это два запроса
    подряд, и порядок между ними — предмет проверки."""

    def __init__(self, card_outcome, slug_outcome=None, name: str = "gog") -> None:
        super().__init__(card_outcome, name)
        self.slug_outcome = slug_outcome
        self.slugs_asked = []

    async def card(self, source_id: str, kind: Kind):
        self.asked.append((source_id, kind))
        return self.outcome

    async def resolve_slug(self, slug: str):
        self.slugs_asked.append(slug)
        return self.slug_outcome


@pytest.fixture
async def loader(sessions):
    def build(client) -> Loader:
        return Loader(library=LibraryRepository(sessions), writer=None,
                      sources=FakeSources(client), posters=None)

    return build


async def test_a_tmdb_link_goes_straight_to_the_card(loader):
    """У TMDB в адресе настоящий идентификатор — превращать нечего."""
    client = FakeCatalog(Found(source_card(Source.TMDB, "157336")), name="tmdb")

    card = await loader(client).card_for_link(
        ExternalLink(source=Source.TMDB, source_id="157336", kind=Kind.MOVIE)
    )

    assert isinstance(card, SourceCard)
    assert client.asked == [("157336", Kind.MOVIE)]
    assert client.slugs_asked == []


async def test_a_gog_slug_becomes_a_number_before_the_card(loader):
    """Ради этого шага задача и существует: каталог по слагу не спросить."""
    client = FakeCatalog(Found(source_card(Source.GOG, "1207658930")),
                         slug_outcome=Found("1207658930"))

    card = await loader(client).card_for_link(
        ExternalLink(source=Source.GOG, source_id="arcanum_of_steamworks",
                     kind=Kind.GAME)
    )

    assert isinstance(card, SourceCard)
    assert client.slugs_asked == ["arcanum_of_steamworks"]
    assert client.asked == [("1207658930", Kind.GAME)]


async def test_an_unresolved_slug_stops_before_the_card(loader):
    """Иначе в каталог ушёл бы слаг, и он ответил бы про чужую игру."""
    client = FakeCatalog(Found(source_card(Source.GOG, "1")),
                         slug_outcome=Missing())

    result = await loader(client).card_for_link(
        ExternalLink(source=Source.GOG, source_id="ничего_такого",
                     kind=Kind.GAME)
    )

    assert isinstance(result, Missing)
    assert client.asked == []


async def test_a_refusal_on_the_slug_is_passed_on(loader):
    refusal = Refusal(source="gog", reason=Reason.NETWORK)
    client = FakeCatalog(Found(source_card(Source.GOG, "1")),
                         slug_outcome=refusal)

    result = await loader(client).card_for_link(
        ExternalLink(source=Source.GOG, source_id="arcanum", kind=Kind.GAME)
    )

    assert result is refusal
    assert client.asked == []


async def test_a_refusal_on_the_card_is_passed_on(loader):
    refusal = Refusal(source="tmdb", reason=Reason.QUOTA)
    client = FakeCatalog(refusal, name="tmdb")

    result = await loader(client).card_for_link(
        ExternalLink(source=Source.TMDB, source_id="157336", kind=Kind.MOVIE)
    )

    assert result is refusal


async def test_a_broken_client_on_the_way_by_link_is_a_refusal(loader, caplog):
    """Сорвавшийся клиент — отказ, а не исключение в интерфейс."""
    client = FakeCatalog(None, name="tmdb")

    async def broken(source_id, kind):
        raise RuntimeError("разбор не удался")

    client.card = broken
    with caplog.at_level("ERROR"):
        result = await loader(client).card_for_link(
            ExternalLink(source=Source.TMDB, source_id="157336", kind=Kind.MOVIE)
        )

    assert isinstance(result, Refusal)
    assert result.reason is Reason.BROKEN


async def test_a_link_to_a_source_without_a_client_is_a_refusal(sessions, caplog):
    """Ссылка на ручную карточку — бессмыслица: клиента у неё нет."""
    load = Loader(library=LibraryRepository(sessions), writer=None,
                  sources=FakeSources(), posters=None)

    with caplog.at_level("WARNING"):
        result = await load.card_for_link(
            ExternalLink(source=Source.MANUAL, source_id="x", kind=Kind.MOVIE)
        )

    assert isinstance(result, Refusal)
    assert "manual" in caplog.text
