"""Три круга загрузки: кандидат становится карточкой в базе."""

import asyncio
from dataclasses import dataclass

import pytest

from backend.model import (
    CardView,
    Credit,
    Found,
    Kind,
    Missing,
    PersonRole,
    Reason,
    Refusal,
    Source,
    SourceCard,
    view_from_hit,
)
from backend.service.cards import CardWriter
from backend.service.loading import Loader
from backend.service.posters import PosterService
from backend.storage.repository.library import LibraryRepository
from backend.storage.repository.views import ViewsRepository
from tests.conftest import (
    PICTURE,
    an_item,
    FakeCatalog,
    FakeSources,
    capture,
    card_parts,
    hit,
    unreachable,
)


# Адреса обложки у кандидата и в детальном ответе разные нарочно: за ней ходят
# двое — загрузчик по адресу выдачи и писатель по адресу детального ответа, — и
# при одном адресе список ушедших запросов у этих двух путей неразличим.
SEARCH_COVER = "https://example.com/p.jpg"
DETAIL_COVER = "https://example.com/d.jpg"


def candidate(source_id="157336", poster=SEARCH_COVER) -> CardView:
    """Кандидат собирается тем же путём, каким приезжает в работе: из выдачи
    поиска через `view_from_hit`. Собранный руками расходился бы с ним молча —
    полноту переноса полей сторожит `test_view_types.py`, а здесь важно, что
    загрузчику достаётся ровно то, что даёт поиск."""
    return view_from_hit(hit(source_id, poster_url=poster))


def source_card(source_id="157336", poster=DETAIL_COVER) -> SourceCard:
    return SourceCard(
        item=an_item(source_id, "Интерстеллар", runtime=169,
                     poster_url=poster),
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


async def test_the_stored_card_takes_both_names(sessions, loader):
    """Пара имён, собранная склейкой, доезжает до базы — иначе она собиралась бы
    впустую.

    Свидетель — путь Steam, ради которого слайс и написан: карточка приходит из
    `appdetails` с `l=russian`, то есть по-русски, а английское имя лежит в
    строке выдачи, куда карточке не дотянуться. Сложить их можно только здесь.

    Карточка сильнее для того языка, который принесла: русское берётся её, а не
    из пары. Английскому взяться у Steam неоткуда, и его даёт пара."""
    rig = loader(Found(SourceCard(item=an_item(
        "292030", "Ведьмак 3: Дикая Охота", kind=Kind.GAME,
        source=Source.STEAM, poster_url=DETAIL_COVER))))
    came = view_from_hit(hit("292030", "The Witcher 3: Wild Hunt",
                             kind=Kind.GAME, source=Source.STEAM,
                             original_title="Ведьмак 3: Дикая Охота",
                             poster_url=DETAIL_COVER))

    item_id = await rig.load.ensure(came)

    stored = await LibraryRepository(sessions).get(item_id)
    assert stored.title == "Ведьмак 3: Дикая Охота"
    assert stored.original_title == "The Witcher 3: Wild Hunt"


async def test_a_lent_cover_address_reaches_the_stored_card(sessions, loader):
    """Адрес обложки, добытой на стороне, доезжает до базы.

    У книги обложку ищет чужой каталог, и в карточке от Google её адреса нет
    вовсе: приезжает он со строкой выдачи. Запиши пустое — и правило
    «потерянная обложка скачается заново по `poster_url`» для книг перестало бы
    выполняться, а на нём стоит порядок удаления двух файлов базы."""
    lent = "https://fantlab.ru/images/editions/orig/118084"
    rig = loader(Found(SourceCard(item=an_item(
        "VOL1", "Пикник на обочине", kind=Kind.BOOK,
        source=Source.GOOGLE_BOOKS, poster_url=""))))
    came = view_from_hit(hit("VOL1", "Пикник на обочине", kind=Kind.BOOK,
                             source=Source.GOOGLE_BOOKS, poster_url=lent))

    item_id = await rig.load.ensure(came)

    stored = await LibraryRepository(sessions).get(item_id)
    assert stored.poster_url == lent


async def test_the_card_wins_over_the_pair_for_its_own_language(sessions, loader):
    """Пара — фоллбек, и карточка сильнее: решение пользователя 03.08.2026.

    В выдаче GOG показал издание — «Ведьмак 3: Дикая Охота - Издание Игра
    Года», — а карточка приезжает с обычным названием. В базу идёт то, что
    принесла карточка.

    Без этого свидетеля «карточка сильнее» неотличимо от «пара сильнее»: в
    соседней проверке русское имя у них совпадает."""
    rig = loader(Found(SourceCard(item=an_item(
        "1207664663", "Ведьмак 3: Дикая Охота", kind=Kind.GAME,
        source=Source.GOG, poster_url=DETAIL_COVER))))
    came = view_from_hit(hit("1207664663",
                             "Ведьмак 3: Дикая Охота - Издание Игра Года",
                             kind=Kind.GAME, source=Source.GOG,
                             original_title="The Witcher 3: Wild Hunt",
                             poster_url=DETAIL_COVER))

    item_id = await rig.load.ensure(came)

    stored = await LibraryRepository(sessions).get(item_id)
    assert stored.title == "Ведьмак 3: Дикая Охота"
    assert stored.original_title == "The Witcher 3: Wild Hunt"


async def test_the_card_beats_the_group_on_the_year(sessions, loader):
    """При записи побеждает год карточки, а не ранний год группы.

    Правило «ранний верен» держится, пока группа — это издания одной игры. Но
    склейка сводит и ремейк с оригиналом: у них одно название буква в букву.
    Замерено на живом Steam — строка «System Shock» это ремейк 2023 года, а из
    группы ей доставался 1994-й от оригинала old-games, и он же уезжал в базу.
    Тем же болели `Prince of Persia` 2008→1990, `Thief` 2014→1998,
    `Silent Hill 2` 2024→2002.

    Карточка тут знает правду: она спрошена по номеру у самого источника."""
    rig = loader(Found(SourceCard(item=an_item(
        "482400", "System Shock", kind=Kind.GAME, source=Source.STEAM,
        year=2023, poster_url=DETAIL_COVER))))
    came = view_from_hit(hit("482400", "System Shock", kind=Kind.GAME,
                             source=Source.STEAM, year=1994,
                             poster_url=DETAIL_COVER))

    item_id = await rig.load.ensure(came)

    stored = await LibraryRepository(sessions).get(item_id)
    assert stored.year == 2023


async def test_the_group_year_fills_a_card_without_one(sessions, loader):
    """Обратная сторона: своего года у карточки может не быть, и тогда берётся
    год пары — иначе строки Steam оставались бы без года вовсе, а это и была
    исходная беда.

    Без этой половины «карточка сильнее» неотличимо от «пару не берём вовсе»."""
    rig = loader(Found(SourceCard(item=an_item(
        "38410", "Fallout 2", kind=Kind.GAME, source=Source.STEAM,
        poster_url=DETAIL_COVER))))
    came = view_from_hit(hit("38410", "Fallout 2", kind=Kind.GAME,
                             source=Source.STEAM, year=1998,
                             poster_url=DETAIL_COVER))

    item_id = await rig.load.ensure(came)

    stored = await LibraryRepository(sessions).get(item_id)
    assert stored.year == 1998


async def test_a_film_keeps_the_original_title_tmdb_gave(sessions, loader):
    """Сборка имени — правило про **игры**, и к кино её применять нельзя.

    У TMDB `original_title` значит другое: там настоящий язык оригинала, а не
    английское название. Раскладка по письменности такого не знает и кладёт в
    поле первое латинское имя — а латинского у «Унесённых призраками» нет ни
    одного, и поле обнулилось бы. Проверено на боевой раскладке: `千と千尋の神隠し`,
    `올드보이` и «Брат» дают пустоту все три.

    Пишется это навсегда — карточка заводится один раз."""
    rig = loader(Found(SourceCard(item=an_item(
        "129", "Унесённые призраками", kind=Kind.MOVIE,
        original_title="千と千尋の神隠し", poster_url=DETAIL_COVER))))
    came = view_from_hit(hit("129", "Унесённые призраками", kind=Kind.MOVIE,
                             original_title="千と千尋の神隠し",
                             poster_url=DETAIL_COVER))

    item_id = await rig.load.ensure(came)

    stored = await LibraryRepository(sessions).get(item_id)
    assert stored.title == "Унесённые призраками"
    assert stored.original_title == "千と千尋の神隠し"


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
        view_from_hit(hit("292030", "Ведьмак", kind=Kind.GAME,
                          source=Source.STEAM))
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
        Kind.MOVIE, Source.TMDB, "157336"
    ) is None


async def test_a_vanished_card_is_missing_and_not_a_refusal(sessions, loader):
    rig = loader(Missing())

    assert isinstance(await rig.load.ensure(candidate()), Missing)


async def test_a_vanished_card_stays_missing_even_if_the_poster_fell_too(
    sessions, loader
):
    """Обложка и карточка спрашиваются разом, и упасть может обложка, пока
    источник отвечает «такого у меня больше нет». Ответ карточки при этом
    старше: «повторите позже» человеку про исчезнувшую карточку — совет,
    которому нельзя последовать, а плашка про недоступную базу уводит от
    настоящей причины.

    Адрес обложки приезжает ещё с выдачей поиска, так что обе половины и правда
    приходят вперегонки."""
    rig = loader(Missing(), poster_status=500)

    assert isinstance(await rig.load.ensure(candidate()), Missing)


async def test_two_refusals_at_once_name_the_source_and_not_its_cdn(
    sessions, loader
):
    """Главный случай — выключенная сеть: падают обе половины разом. Наверх
    обязан ехать отказ карточки, а не обложки: плашка называет человеку
    источник, и «сеть до CDN не дошла» вместо «источник недоступен» уводит от
    настоящей причины."""
    rig = loader(Refusal(source="tmdb", reason=Reason.NETWORK),
                 poster_status=500)

    result = await rig.load.ensure(candidate())

    assert isinstance(result, Refusal)
    assert result.source == "tmdb"


async def test_a_game_without_a_vertical_cover_is_still_written(sessions, loader,
                                                                posters):
    """У Steam адрес обложки не приезжает в ответе — он собирается нами по
    образцу, и у части приложений такой картинки нет вовсе. Замерено живьём
    02.08.2026: у «Ведьмака 3», Counter-Strike, REDkit и Ultima Underworld CDN
    отвечает `200`, у дополнения GTA V и служебного клиента Steam — `404`.

    Постоянный `404` отказом быть не может: карточка тогда не пишется вовсе, а
    «повторим при следующем показе» не наступает никогда — добавить такую игру
    было бы нельзя ни разу. Обложки просто нет, и карточка живёт без неё; так же
    ведёт себя пустой адрес у TMDB и GOG."""
    rig = loader(Found(source_card(poster=SEARCH_COVER)), poster_status=404)

    item_id = await rig.load.ensure(candidate())

    assert isinstance(item_id, int), f"карточка не завелась: {item_id}"
    assert await posters.has(item_id) is False
    # Запрос ровно один: писателю «обложки нет» и «обложку не добывали» —
    # разные вещи, и на первом он в CDN не идёт. Сходи он туда второй раз,
    # судьбу карточки решал бы второй ответ: сетевая икота между запросами
    # вернула бы отказ, и карточка не записалась бы — то есть ровно то, ради
    # снятия чего проверка и написана.
    assert len(rig.requests) == 1


async def test_an_unreachable_cdn_keeps_its_reason(sessions, engine, posters):
    """«Нет связи» и «ответил непонятно чем» решаются наверху по-разному, и
    причина обязана дойти нетронутой.

    Проверяется у загрузчика: обложку добывает он, а писатель её только пишет —
    со своим добыванием у писателя было два разных смысла у одного `None`."""
    parts = card_parts(sessions, posters, unreachable())
    load = Loader(library=LibraryRepository(sessions),
                  writer=CardWriter(**parts),
                  sources=FakeSources(FakeCatalog(Found(source_card()))),
                  posters=parts["posters"])

    result = await load.ensure(candidate())
    await parts["posters"].aclose()

    assert isinstance(result, Refusal)
    assert result.reason is Reason.NETWORK


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
        Kind.MOVIE, Source.TMDB, "157336"
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
        Kind.MOVIE, Source.TMDB, "157336"
    ) is None
    assert [r for r in caplog.records
            if r.name.startswith("backend") and r.levelname == "ERROR"] == []
    # Запрос один и по адресу кандидата: узнав отказ, загрузчик не пускает
    # писателя за той же обложкой ещё раз, а тот пошёл бы по адресу детального
    # ответа. Без этой проверки досрочный выход из `ensure` не наблюдается
    # ничем — карточки не будет в обоих случаях.
    assert [str(one.url) for one in rig.requests] == [SEARCH_COVER]


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
    # Адреса у кандидата нет, значит единственный ушедший запрос — писательский.
    assert [str(one.url) for one in rig.requests] == [DETAIL_COVER]


async def test_the_cover_is_fetched_once_and_by_the_loader(sessions, loader):
    """Ради этого круги и идут разом: обложку скачивает загрузчик по адресу из
    выдачи и передаёт писателю готовой. Не передай — писатель полез бы за ней
    сам, уже по адресу детального ответа.

    Проверяется и число запросов, и адрес: по одному числу эти два пути
    неразличимы — запрос всё равно один, просто чужой.

    Тем же проходом сторожится вторая половина доливки: в базу уезжает адрес
    **карточки**, а не тот, по которому качали. Переставь стороны в
    `_from_both`, и у Steam в базу навсегда легло бы угаданное имя файла из
    выдачи — неверное у 38% игр, а перезапроса у игр не бывает."""
    rig = loader(Found(source_card()))

    item_id = await rig.load.ensure(candidate())

    assert [str(one.url) for one in rig.requests] == [SEARCH_COVER]
    stored = await LibraryRepository(sessions).get(item_id)
    assert stored.poster_url == DETAIL_COVER


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

    async def watched(source, url, kind):
        order.append("обложка началась")
        return await fetch(source, url, kind)

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
