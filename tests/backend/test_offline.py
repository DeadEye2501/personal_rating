"""Главное обещание приложения: без сети работает всё, кроме поиска чужого.

Собранный бэкенд проверяется соседним модулем, `test_assembly.py`: там про
проводку частей друг к другу, здесь — про то, что человек ими делает."""


from backend.model import (
    CompanyRole,
    Credit,
    Filters,
    Kind,
    PersonRole,
    Reason,
    Source,
    SourceCard,
    new_manual_item,
)
from tests.conftest import (
    MOMENT,
    PICTURE,
    RATED,
    WANTED,
    an_item,
)


def mine(title: str, kind: Kind = Kind.MOVIE, **fields):
    """`new_manual_item` не подставляет `synced_at` сама — поле у `Item`
    обязательное, и передавать его должен вызывающий."""
    return new_manual_item(kind, title, synced_at=MOMENT, **fields)


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
    tag_id = await offline.tags.create(Kind.MOVIE, "Пересмотреть")

    await offline.tags.assign(item_id, tag_id)

    assert [tag.name for tag in await offline.tags.tags_of(item_id)] == [
        "Пересмотреть"
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
