"""Собранный бэкенд: что к чему приведено в `build_backend`.

Отдельным модулем от обещания офлайна: там про то, что человек делает с
приложением, здесь — про проводку его частей. Разошлись они по этому шву, когда
файл перевалил предел в пятьсот строк.

Сборка — самое опасное место проекта: из двенадцати мутаций по ней девять
однажды прошли молча, и приложение «работало» с перепутанными людьми и студиями,
с незакрытыми соединениями и с транспортом, не доехавшим до постерных клиентов.
"""

import httpx
import pytest

from backend.app import build_backend
from backend.config import load_config
from backend.model import (
    CompanyRole,
    ExternalId,
    ExternalLink,
    GenreKind,
    IdSource,
    Kind,
    PersonRole,
    Reason,
    Refusal,
    Source,
    new_manual_item,
    view_from_hit,
)
from backend.service.posters import LENDERS, POSTER_SOURCES
from backend.sources.registry import ROUTES
from backend.storage.posters import NotOpened
from backend.storage.repository.external import (
    ExternalIdsRepository,
    ExternalRatingsRepository,
)
from backend.storage.session import session_factory
from tests.backend.conftest import assemble
from tests.conftest import (
    MOMENT,
    PICTURE,
    an_item,
    hit,
    recorded,
    unreachable,
)


def mine(title: str, kind: Kind = Kind.MOVIE, **fields):
    """`new_manual_item` не подставляет `synced_at` сама — поле у `Item`
    обязательное, и передавать его должен вызывающий."""
    return new_manual_item(kind, title, synced_at=MOMENT, **fields)


async def test_every_poster_source_got_its_own_named_client(offline):
    """Отказ постерного клиента называет свой источник, и у всех источников
    имена разные.

    Иначе сорвавшуюся обложку не отличить от чужой в логе — то же, чем однажды
    обернулось общее `imdb` у двух оценочных клиентов. Проверяется собранный
    бэкенд: своя ветка на источник живёт в сборке, и тесты сервиса обложек, у
    которых клиенты свои, до неё не добираются.

    Причина отказа сторожится тем же проходом и по двум поводам сразу. Сетевая
    она потому, что транспорт доехал до постерных клиентов: не доедь он — сюда
    встал бы настоящий, и адрес `example.com` ответил бы кодом, а не обрывом.
    Источник, которому в сборке не досталось клиента, дал бы `BROKEN`.

    Набор берётся из `POSTER_SOURCES`, а не переписывается литералом: второй
    список тех же источников разошёлся бы с первым молча."""
    named = set()
    for source in POSTER_SOURCES:
        result = await offline.posters.poster_for(
            None, source, "https://example.com/p.jpg", MOMENT, Kind.MOVIE
        )
        assert isinstance(result, Refusal), f"{source}: обложку никто не просил"
        assert result.reason is Reason.NETWORK, f"{source}: клиента нет в наборе"
        assert str(source) in result.source
        named.add(result.source)

    assert len(named) == len(POSTER_SOURCES)


async def test_the_built_backend_downloads_a_lent_cover_by_its_own_client(offline):
    """Боевая сборка, а не двойник: соединение под чужой адрес заводится в
    `app.py`, и тесты сервиса обложек со своими клиентами до неё не добираются.

    Не заведись оно — обложка с fantlab.ru поехала бы постерным соединением
    Google, и сетевая беда на одном сайте закрывала бы обложки другого."""
    answer = await offline.posters.fetch(
        Source.GOOGLE_BOOKS, "https://fantlab.ru/images/editions/orig/7",
        Kind.BOOK)

    assert isinstance(answer, Refusal)
    assert answer.reason is Reason.NETWORK, "транспорт не доехал до заимодавца"
    assert "fantlab" in answer.source, f"отказ назвал не того: {answer.source}"


async def test_every_lender_the_registry_names_has_its_own_connection():
    """Заимодавец объявлен дважды: реестр знает, **кто** ищет обложку, когда
    каталог её не дал, а сервис обложек — **чьим соединением** её потом качать.

    Разъедься эти два объявления, и адрес нового заимодавца поехал бы
    соединением источника карточки: беда буква в букву та, которую чинили
    правкой про FantLab, и молчала бы она так же. Соседняя проверка сторожит
    одного заимодавца поимённо, а эта — что поимённых хватает на всех.

    Половину сторожить нечем, и это стоит знать: маршрут решает **ключ**
    `LENDERS` — хост, — а сверяется здесь значение, имя. Заимодавец с верным
    именем и неверным хостом пройдёт и эту проверку, и весь набор. Держит эту
    половину правило, а не тест: хост берётся из адреса самого клиента (у
    FantLab — из `ORIGINAL`), и второго заводить надо так же."""
    named = {route.covers for route in ROUTES.values() if route.covers}

    assert named, "запасных источников обложки не осталось — сторож устарел"
    assert named <= set(LENDERS.values()), f"без соединения: {named - set(LENDERS.values())}"


async def test_the_built_backend_asks_google_for_books(offline):
    """Боевая сборка, а не двойник: разъедься имя постерного соединения со
    значением `Source`, и книга осталась бы без обложки при зелёном наборе, а
    без обложки карточка не пишется вовсе.

    Проверяются оба конца проводки: каталог, который спросит поиск, и клиент
    обложек, которого спросит писатель."""
    assert offline._sources.catalog_for(Kind.BOOK) == [
        offline._sources.google_books]
    assert Source.GOOGLE_BOOKS in offline.posters._clients


async def test_the_data_folder_is_made_if_it_is_not_there(tmp_path):
    """Первый запуск на чистой машине: папки данных ещё нет. Хранилище постеров
    само её не создаёт — sqlite просто не откроется."""
    fresh = tmp_path / "Которой-нет"
    config = load_config({"DATA_DIR": str(fresh)}, base_dir=tmp_path)

    backend = await build_backend(config,
                                  transport=unreachable())
    await backend.aclose()

    assert (fresh / "posters.db").exists()


async def test_the_enrichment_asks_nobody_without_the_network(offline):
    """Третий круг без сети не пишет в базу ничего: отказ — не «у источника
    нет», и через неделю пустая строка не должна выдать себя за ответ.

    Идентификатор карточке нужен обязательно: без него обогащение выходит до
    первого вопроса, и оборванная сеть в проверке не участвует вовсе — а это
    единственное место, где сходятся настоящие клиенты, реестр и мёртвая сеть.

    Репозитории собираются здесь, а не берутся у `Backend`: на границе слоёв их
    нет, клиенту они не нужны."""
    sessions = session_factory(offline._engine)
    item_id = await offline.library.create(mine("Своё"))
    await ExternalIdsRepository(sessions).put(
        item_id, ExternalId(IdSource.IMDB, "tt0816692")
    )

    ratings = await offline.enricher.enrich(item_id, Kind.MOVIE)

    assert ratings == []
    assert await ExternalRatingsRepository(sessions).ratings_of(item_id) == []


async def test_the_assembly_wires_the_three_services_nobody_asked_about(offline):
    """Сборка — самое опасное место проекта: `loader=None` оставлял весь набор
    зелёным, потому что боевой `Backend` про эти три поля не спрашивали нигде.
    Остальные его поля сторожат тесты выше — каждое своим делом.

    Ответы разные и нарочно: справочник жанров читается из базы и работает
    офлайн, загрузка по ссылке упирается в мёртвую сеть, а перезапрос сериала у
    ручной карточки заканчивается, не дойдя до сети. Ни одного из трёх не
    получить, если поле осталось пустым или в него передали соседа."""
    assert await offline.genres.list_for_kind(GenreKind.FILM) == [], (
        "Схема поднята без миграций, справочник пуст")

    # У перезапроса сериала возвращаемого значения нет вовсе, и наблюдать надо
    # след: он ходит в сеть, а сеть мертва — значит момент синхронизации обязан
    # остаться прежним. Сериал берём от TMDB: ручной и кино выходят из `refresh`
    # на первой же проверке, не дойдя ни до сети, ни до записи.
    series_id = await offline.library.create(
        an_item("1396", "Во все тяжкие", kind=Kind.SERIES, synced_at=MOMENT)
    )
    await offline.series.refresh(series_id)
    assert (await offline.library.get(series_id)).synced_at == MOMENT

    link = await offline.loader.card_for_link(
        ExternalLink(Source.TMDB, "157336", Kind.MOVIE)
    )
    assert isinstance(link, Refusal)
    assert link.reason is Reason.NETWORK


async def test_the_assembly_gives_the_loader_its_poster_clients(tmp_path):
    """Пятое поле того же рода: боевой загрузчик со своей службой обложек.

    Проверок у него не было вовсе — единственная, трогавшая боевой `loader`,
    ходит по ссылке, а этот путь обложек не касается. Пустой набор клиентов
    **у самого загрузчика** не наблюдался ничем, а с ним завести найденную
    поиском карточку было бы нельзя ни одну: обложка отвечала бы «нет клиента»,
    и писатель не писал бы ничего. Пустые клиенты в сборке ловит сосед —
    `test_every_poster_source_got_its_own_named_client`, — но он спрашивает
    службу обложек напрямую, минуя загрузчик.

    Сеть тут живая нарочно: с мёртвой отказала бы карточка, и до обложки дело не
    дошло бы — проверять было бы нечего."""
    def handler(request: httpx.Request) -> httpx.Response:
        if "themoviedb.org" in request.url.host:
            return httpx.Response(200, json=recorded("tmdb/movie_detail.json"))
        return httpx.Response(200, content=PICTURE)

    backend = await assemble(tmp_path, transport=httpx.MockTransport(handler))
    try:
        item_id = await backend.loader.ensure(
            view_from_hit(hit(poster_url="https://image.tmdb.org/p.jpg")))

        assert isinstance(item_id, int), f"карточка не завелась: {item_id}"
        assert await backend.posters.has(item_id), "обложка не доехала"
    finally:
        await backend.aclose()


async def test_the_assembly_wires_the_click_on_a_name(offline):
    """Четвёртое поле того же рода: `finder=None` оставлял весь набор зелёным —
    боевую сборку клика не звал ни один тест.

    Домены проверяются оба и по отдельности: подай сюда сборка людей вместо
    студий, поиск по человеку пошёл бы в таблицу студий, там этой строки нет — и
    ответ пришёл бы пустым. Номера у человека и студии для этого разведены: обе
    таблицы нумеруются с единицы, и с равными номерами обмен сошёлся бы."""
    item_id = await offline.library.create(mine("Домашнее видео"))
    person_id = await offline.people.create_manual("Кристофер Нолан")
    for number in range(3):
        await offline.companies.create_manual(f"Лишняя {number}")
    studio_id = await offline.companies.create_manual("Syncopy")
    await offline.people.attach(item_id, person_id, PersonRole.DIRECTOR)
    await offline.companies.attach(item_id, studio_id, CompanyRole.PUBLISHER)

    by_person = await offline.finder.by_entity("people", person_id, Kind.MOVIE)
    by_studio = await offline.finder.by_entity("companies", studio_id, Kind.MOVIE)

    assert [view.item_id for view in by_person.views] == [item_id]
    assert [view.item_id for view in by_studio.views] == [item_id]

    # Внешняя половина наблюдается отказом: сеть тут мертва, и отказ появляется
    # ровно тогда, когда сервису достался настоящий клиент от настоящего
    # реестра. Без этой строки `people_for(MOVIE) → None` осталось бы зелёным.
    assert [one.source for one in by_person.refusals] == ["tmdb"]
    assert by_studio.refusals == ()


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
    # Закрытое хранилище отказывает своим отказом, а не любой ошибкой: широкий
    # `Exception` поймал бы и опечатку в самом тесте, и закрытие осталось бы
    # непроверенным. Окажись хранилище способно открыться заново — тест
    # покраснеет, и это правильный сигнал: закрытие тогда не закрытие.
    # Спрашивается публичным путём: второй файл базы наружу не показывается, и
    # `has` уходит в то же закрытое хранилище.
    with pytest.raises(NotOpened):
        await backend.posters.has(1)
    for connection in backend._sources.connections:
        with pytest.raises(RuntimeError):
            await connection.get("https://example.invalid/")


async def test_closing_twice_is_quiet(tmp_path):
    """Фикстура закрывает бэкенд после теста, и тест может закрыть его сам."""
    backend = await assemble(tmp_path)

    await backend.aclose()
    await backend.aclose()
