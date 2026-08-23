"""Главное обещание приложения: без сети работает всё, кроме поиска чужого."""

import httpx
import pytest

from backend.app import build_backend
from backend.config import load_config
from backend.model import (
    CompanyRole,
    Credit,
    ExternalId,
    ExternalLink,
    Filters,
    GenreKind,
    IdSource,
    Kind,
    PersonRole,
    Reason,
    Refusal,
    Source,
    SourceCard,
    new_manual_item,
    view_from_hit,
)
from backend.service.posters import POSTER_SOURCES
from backend.storage.posters import NotOpened
from backend.storage.repository.external import (
    ExternalIdsRepository,
    ExternalRatingsRepository,
)
from backend.storage.session import create_engine, session_factory
from backend.storage.tables import metadata
from tests.conftest import (
    MOMENT,
    hit,
    PICTURE,
    RATED,
    WANTED,
    an_item,
    recorded,
    unreachable,
)


def mine(title: str, kind: Kind = Kind.MOVIE, **fields):
    """`new_manual_item` не подставляет `synced_at` сама — поле у `Item`
    обязательное, и передавать его должен вызывающий."""
    return new_manual_item(kind, title, synced_at=MOMENT, **fields)


async def assemble(tmp_path, transport=None):
    engine = create_engine(tmp_path / "library.db")
    async with engine.begin() as connection:
        await connection.run_sync(metadata.create_all)
    await engine.dispose()

    config = load_config({"DATA_DIR": str(tmp_path)}, base_dir=tmp_path)
    return await build_backend(config, transport=transport or unreachable())


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
    и при исчерпанной квоте, и спутать их нельзя.

    Имя отказавшего — здесь же, и это единственное место, где сверяется привязка
    имени соединения к клиенту: перепутай их местами в сборке, и человеку скажут
    «Steam» про отказавший TMDB, а исчерпанная квота выключит не тот источник."""
    result = await offline.search.external(Kind.MOVIE, "интерстеллар")

    assert result.views == ()
    assert [r.reason for r in result.refusals] == [Reason.NETWORK]
    assert [r.source for r in result.refusals] == ["tmdb"]


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


async def test_a_hand_made_card_lands_in_the_wishlist(offline):
    """Заведённая руками карточка не пропадает с глаз. В «Оценённые» её не
    пускает отсутствие оценки, и без закладки её не показывает ни один раздел:
    человек нажал «+», заполнил окно, сохранил — и не нашёл сохранённого.

    Кандидат выдачи лежит здесь же и обязан остаться за бортом: пишется он тем
    же `library.create`, и положи закладку туда — список дел заполнили бы
    карточки, которых никто не заводил. Показанная строка заводится сама, по
    одному показу."""
    await offline.library.create(mine("Мелькнул в выдаче"))

    await offline.create_manual_card(mine("Своё, руками"), now=MOMENT)
    page = await offline.feed.page(WANTED)

    assert [view.title for view in page] == ["Своё, руками"]


async def test_a_new_card_does_not_inherit_a_cover_left_by_a_deleted_one(offline):
    """`item` заведён без `AUTOINCREMENT`, и удалённый номер SQLite выдаёт
    повторно. Обложка лежит во втором файле базы, где внешних ключей не бывает,
    и пережить свою карточку она может: скачивание живёт до двадцати секунд, а
    доехавшие байты записываются уже после удаления.

    Найденную в хранилище обложку никто не перекачивает, поэтому чужая осталась
    бы у новой карточки навсегда. Проверяется на собранном бэкенде: порознь
    репозиторий и хранилище друг о друге не знают вовсе."""
    gone = await offline.library.create(mine("Ушедшая"))
    await offline.delete_card(gone)
    # Обложка, доехавшая после удаления: карточки уже нет, помешать некому.
    await offline.posters.save(gone, PICTURE, now=MOMENT)
    assert await offline.posters.has(gone) is True, "сирота не легла — нечего убирать"

    fresh = await offline.create_manual_card(mine("Свежая"), now=MOMENT)

    assert fresh == gone, "номер не выдался повторно — проверка ни о чём"
    assert await offline.posters.has(fresh) is False


async def test_tags_are_edited(offline):
    item_id = await offline.library.create(mine("Своё"))
    tag_id = await offline.tags.create(Kind.MOVIE, "пересмотреть")

    await offline.tags.assign(item_id, tag_id)

    assert [tag.name for tag in await offline.tags.tags_of(item_id)] == [
        "пересмотреть"
    ]


async def test_a_card_is_deleted_with_everything_of_mine(offline):
    """Обложка проверяется здесь же: она лежит во втором файле базы и каскадом
    не уходит, а через собранный бэкенд это единственное место, где видно, что
    удаление добралось до обоих файлов."""
    item_id = await offline.library.create(mine("Своё"))
    await offline.ratings.set_score(item_id, 8.0, now=MOMENT)
    await offline.posters.save(item_id, PICTURE, now=MOMENT)

    await offline.delete_card(item_id)

    assert await offline.library.get(item_id) is None
    assert await offline.ratings.get(item_id) is None
    assert await offline.posters.has(item_id) is False


async def test_the_delete_button_remembers_what_was_taken_away(offline):
    """Главное следствие задачи 4 достигается ровно здесь: страница зовёт через
    мост `Backend.delete_card`, других вызовов `discard_card` в боевом коде нет.

    Соседние проверки удаления берут ручную карточку, а у неё `remember`
    выходит первой же строкой — разницы между `discard_card` и `remove_card`
    там нет **по построению**, и подмена одного другим оставалась зелёной.
    Поэтому карточка здесь чужая, из магазина.

    Память спрашивается у самого репозитория, а не через выдачу поиска:
    внешняя выдача требует сети, а этот файл проверяет обещание «без сети
    работает всё, кроме поиска чужого». Поле приватное намеренно — через
    границу слоёв его не отдают, — и лезем в него только отсюда, из проверки
    самой сборки."""
    mark = (Kind.GAME, Source.STEAM, "570")
    gone = await offline.library.create(
        an_item("570", "Dota 2", kind=Kind.GAME, source=Source.STEAM)
    )

    await offline.delete_card(gone)

    assert await offline._removed.known([mark]) == {mark}


async def test_a_single_card_can_be_redrawn(offline):
    """После загрузки кандидата и после простановки оценки ленте нужно
    перерисовать одну карточку. Спросить её больше негде: `page` умеет только
    страницу раздела, `local` — только по строке запроса."""
    item_id = await offline.library.create(mine("Своё"))
    await offline.ratings.set_score(item_id, 7.0, now=MOMENT)

    views = await offline.feed.views_of([item_id])

    assert views[0].rating.score == 7.0


async def test_the_cast_of_a_hand_made_card_is_kept(offline):
    """Люди и студии — два разных репозитория с одинаковым устройством, и в
    сборке их легко поменять местами. Тогда актёр уехал бы в студии, а тесты
    репозиториев этого не увидели бы: там их собирают по отдельности."""
    item_id = await offline.library.create(mine("Своё"))
    actor = await offline.people.create_manual("Мэттью Макконахи")
    studio = await offline.companies.create_manual("Syncopy")
    await offline.people.attach(item_id, actor, PersonRole.ACTOR, 0)
    await offline.companies.attach(item_id, studio, CompanyRole.PUBLISHER)

    view = (await offline.feed.views_of([item_id]))[0]

    assert [credit.name for credit in view.people] == ["Мэттью Макконахи"]
    assert [credit.name for credit in view.companies] == ["Syncopy"]


async def test_the_tracks_of_a_hand_made_album_are_kept(offline):
    """Треки заводит и показывает разный код: пишет их свой репозиторий, а
    приезжают они пачечным чтением ленты. Не позови сборка одного из двух — и
    альбом сохранится, а список окажется пустым при зелёных тестах обеих
    половин: свои они собирают сами.

    Порядок проверяется списком: он часть данных, и записан не по алфавиту."""
    item_id = await offline.library.create(mine("A Night at the Opera",
                                                kind=Kind.MUSIC))
    await offline.tracks.replace(
        item_id, ["Bohemian Rhapsody", "Love of My Life", "'39"])

    view = (await offline.feed.views_of([item_id]))[0]

    assert view.tracks == ("Bohemian Rhapsody", "Love of My Life", "'39")


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

    view = (await offline.feed.views_of([item_id]))[0]
    assert (view.year, view.source_id) == (2014, "157336")
    assert [credit.name for credit in view.people] == ["Кристофер Нолан"]
    assert view.companies == ()


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
            None, source, "https://example.com/p.jpg", MOMENT
        )
        assert isinstance(result, Refusal), f"{source}: обложку никто не просил"
        assert result.reason is Reason.NETWORK, f"{source}: клиента нет в наборе"
        assert str(source) in result.source
        named.add(result.source)

    assert len(named) == len(POSTER_SOURCES)


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
    fresh = tmp_path / "которой-нет"
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
        "схема поднята без миграций, справочник пуст")

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
