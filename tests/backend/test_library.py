from dataclasses import replace
from datetime import date

import pytest
from sqlalchemy import text

from backend.model import Item, Kind, Source
from backend.storage.repository.library import ItemExists, LibraryRepository
from backend.storage.repository.ratings import RatingsRepository
from backend.storage.repository.tags import TagsRepository
from backend.storage.repository.wishlist import WishlistRepository
from tests.conftest import LATER, MOMENT as WHEN
from tests.conftest import an_item


def make_item(**overrides) -> Item:
    """Умолчания общего `an_item` плюс год: здесь он участвует в сортировках."""
    return an_item(**({"source_id": "157336", "title": "Интерстеллар",
                       "year": 2014} | overrides))


async def test_create_inserts_and_returns_an_identifier(sessions):
    repository = LibraryRepository(sessions)
    item_id = await repository.create(make_item())
    assert item_id > 0

    stored = await repository.get(item_id)
    assert stored.title == "Интерстеллар"
    assert stored.year == 2014


async def test_creating_the_same_identity_twice_is_refused(sessions):
    """Идентичность занята — дубль не заводим. На этом же ограничении стоит
    отказ привязать карточку к уже имеющейся внешней."""
    repository = LibraryRepository(sessions)
    await repository.create(make_item())
    with pytest.raises(ItemExists):
        await repository.create(make_item(title="Interstellar"))

    # Отказ не должен оставить после себя половину записи.
    assert len(await repository.list_by_kind(Kind.MOVIE, limit=50, offset=0)) == 1


async def in_both_stores(repository) -> tuple[int, int]:
    """Одна игра под одним номером в двух магазинах: `500810` есть и там, и там.

    Разводит два разных случая — что это не конфликт при заведении и что поиск
    без источника опознать её не может."""
    return (
        await repository.create(
            make_item(kind=Kind.GAME, source=Source.STEAM, source_id="500810",
                      title="Arcanum в Steam")
        ),
        await repository.create(
            make_item(kind=Kind.GAME, source=Source.GOG, source_id="500810",
                      title="Arcanum в GOG")
        ),
    )


async def test_same_source_id_in_different_sources_is_not_a_conflict(sessions):
    repository = LibraryRepository(sessions)
    steam, gog = await in_both_stores(repository)
    assert steam != gog


async def test_every_field_survives_the_round_trip(sessions):
    """Карточка сравнивается целиком, а не по нескольким полям: выпади любое
    из тринадцати по дороге в базу или обратно — вернётся умолчание, и равенство
    не сойдётся. Проверка по одному полю пропустила бы те, о которых забыли."""
    repository = LibraryRepository(sessions)
    written = make_item(
        kind=Kind.SERIES, source=Source.MANUAL, source_id="83867",
        title="Andor", original_title="Andor: A Star Wars Story",
        year=2022, released_at=date(2022, 9, 21),
        synopsis="Пять лет до восстания.", poster_url="/andor.jpg",
        runtime=48, seasons_count=2, episodes_count=24,
    )
    item_id = await repository.create(written)

    stored = await repository.get(item_id)
    assert stored == replace(written, id=item_id)


async def test_texts_written_past_the_repository_come_back_empty(sessions, stored):
    """Пустая колонка отдаётся пустой строкой, а не `None`: иначе `None` уехал
    бы в интерфейс и показался словом «None».

    Строка заводится мимо репозитория — он-то кладёт пустые строки, а не NULL,
    и через него эта ветка недостижима. Так в базу попадают карточки, правленные
    не им: ручная правка и доливка данных из второго источника."""
    repository = LibraryRepository(sessions)
    item_id = await stored("item")

    found = await repository.get(item_id)
    assert (found.original_title, found.synopsis, found.poster_url) == ("", "", "")


async def test_a_null_title_does_not_break_the_search_for_duplicates(sessions, stored):
    """`py_lower` зовут и на NULL, и без ветки под него поиск падает
    `OperationalError` — на карточке, у которой просто нет оригинального
    названия."""
    repository = LibraryRepository(sessions)
    await stored("item")

    assert await repository.find_by_title(Kind.MOVIE, "Интерстеллар") != []


async def test_enumerations_are_stored_as_their_plain_values(sessions, engine):
    """Значения перечислений — часть схемы: по ним идут выборки и фильтры.
    Читается сырая колонка, потому что обратное превращение при чтении
    подменённое значение вернуло бы обратно и скрыло подмену."""
    repository = LibraryRepository(sessions)
    await repository.create(make_item(kind=Kind.SERIES, source=Source.MANUAL))

    async with engine.connect() as connection:
        row = (await connection.execute(text("SELECT kind, source FROM item"))).one()
    assert tuple(row) == ("series", "manual")


async def test_kind_and_source_come_back_as_enumerations(sessions):
    """В базе они лежат текстом. Вернувшись строкой, карточка сравнилась бы с
    `Kind.SERIES` по значению и обманула бы тест, но перестала бы быть тем, что
    обещает тип на границе слоёв."""
    repository = LibraryRepository(sessions)
    item_id = await repository.create(
        make_item(kind=Kind.SERIES, source=Source.MANUAL, source_id="1")
    )
    stored = await repository.get(item_id)
    assert isinstance(stored.kind, Kind)
    assert isinstance(stored.source, Source)


async def test_get_picks_the_asked_card_and_not_just_any(sessions):
    """На пустой базе «взять что попало» и «не найти» неразличимы, поэтому
    рядом лежат соседи: без сравнения с `id` выборка вернула бы первого."""
    repository = LibraryRepository(sessions)
    identifiers = [
        await repository.create(make_item(source_id=str(number), title=f"Фильм {number}"))
        for number in range(3)
    ]

    found = await repository.get(identifiers[2])
    assert (found.id, found.title) == (identifiers[2], "Фильм 2")
    assert await repository.get(max(identifiers) + 1) is None


async def test_find_by_source_takes_the_source_into_account(sessions):
    """Номер сам по себе карточку не опознаёт: `500810` есть и в Steam, и в
    GOG, и это разные игры."""
    repository = LibraryRepository(sessions)
    await in_both_stores(repository)

    found = await repository.find_by_source(Source.GOG, "500810")
    assert found.title == "Arcanum в GOG"


async def test_find_by_source(sessions):
    repository = LibraryRepository(sessions)
    await repository.create(make_item())
    found = await repository.find_by_source(Source.TMDB, "157336")
    assert found.title == "Интерстеллар"
    assert await repository.find_by_source(Source.TMDB, "1") is None


async def test_lists_give_out_cards_and_not_rows(sessions):
    """Наружу едет `Item`, а не строка базы. Поймать это можно только типом:
    `Row` притворяется и кортежем, и объектом с полями, поэтому сравнение имён
    и значений сходится и на нём."""
    repository = LibraryRepository(sessions)
    await repository.create(make_item(title="Ведьмак"))

    for found in (
        await repository.list_by_kind(Kind.MOVIE, limit=50, offset=0),
        await repository.find_by_title(Kind.MOVIE, "ведьмак"),
    ):
        assert [type(one) for one in found] == [Item]


async def test_list_by_kind_ignores_other_kinds(sessions):
    repository = LibraryRepository(sessions)
    await repository.create(make_item())
    await repository.create(
        make_item(kind=Kind.GAME, source=Source.STEAM, source_id="1", title="Игра")
    )
    movies = await repository.list_by_kind(Kind.MOVIE, limit=50, offset=0)
    assert [item.title for item in movies] == ["Интерстеллар"]


async def test_the_window_moves_and_never_repeats_a_card(sessions):
    """Порция берётся окном, и порядок обязан быть устойчивым: без него вторая
    страница отдала бы то же, что первая, а лента показала бы карточку дважды."""
    repository = LibraryRepository(sessions)
    # Порядок заведения нарочно не алфавитный: совпади он — тест зеленел бы и
    # вовсе без сортировки, на порядке строк в файле базы.
    for number in (3, 0, 4, 1, 2):
        await repository.create(
            make_item(source_id=str(number), title=f"Фильм {number}")
        )

    first = await repository.list_by_kind(Kind.MOVIE, limit=2, offset=0)
    second = await repository.list_by_kind(Kind.MOVIE, limit=2, offset=2)
    assert [item.title for item in first] == ["Фильм 0", "Фильм 1"]
    assert [item.title for item in second] == ["Фильм 2", "Фильм 3"]


async def test_find_by_title_matches_original_title_within_one_kind(sessions):
    """Предупреждение о совпадении: сравнение по обоим названиям и только
    внутри своего типа — фильм «Ведьмак» и игра «Ведьмак» не дубли."""
    repository = LibraryRepository(sessions)
    await repository.create(
        make_item(title="Ведьмак", original_title="The Witcher", source_id="1")
    )
    await repository.create(
        make_item(kind=Kind.GAME, source=Source.STEAM, source_id="2",
                  title="Ведьмак")
    )

    hits = await repository.find_by_title(Kind.MOVIE, "the witcher")
    assert [item.title for item in hits] == ["Ведьмак"]

    assert await repository.find_by_title(Kind.SERIES, "Ведьмак") == []


async def test_find_by_title_ignores_case_in_russian(sessions):
    """Встроенный lower() в SQLite умеет только ASCII. Без своей функции
    предупреждение о дубле не срабатывало бы ни на одном русском названии —
    и тест, ищущий по латинскому оригиналу, этого бы не заметил."""
    repository = LibraryRepository(sessions)
    await repository.create(make_item(title="Ведьмак", source_id="1"))

    for needle in ("ведьмак", "ВЕДЬМАК", "  Ведьмак  "):
        hits = await repository.find_by_title(Kind.MOVIE, needle)
        assert [item.title for item in hits] == ["Ведьмак"], needle


async def test_find_by_title_matches_whole_titles_only(sessions):
    """Совпадение — это совпадение целиком: «Ведьмак» и «Ведьмак 3» разные
    карточки, и предупреждать о дубле на второй незачем. Положительная половина
    рядом: без неё пустой ответ на любой запрос сошёл бы за верный."""
    repository = LibraryRepository(sessions)
    await repository.create(make_item(title="Ведьмак 3", source_id="1"))

    assert await repository.find_by_title(Kind.MOVIE, "Ведьмак") == []
    hits = await repository.find_by_title(Kind.MOVIE, "Ведьмак 3")
    assert [item.title for item in hits] == ["Ведьмак 3"]


async def test_refresh_touches_only_seasons_and_episodes(sessions):
    """Спека прямо запрещает автоматически переписывать остальное."""
    repository = LibraryRepository(sessions)
    item_id = await repository.create(
        make_item(kind=Kind.SERIES, source_id="83867", title="Андор",
                  original_title="Andor", synopsis="мой текст",
                  poster_url="/andor.jpg", year=2022, runtime=48,
                  released_at=date(2022, 9, 21),
                  seasons_count=1, episodes_count=12)
    )

    await repository.refresh_series_counts(item_id, 2, 24, now=LATER)

    stored = await repository.get(item_id)
    assert (stored.seasons_count, stored.episodes_count) == (2, 24)
    assert stored.synced_at == LATER
    # Всё остальное — человеку: перезаписывать это автоматически нельзя.
    assert stored == replace(
        make_item(kind=Kind.SERIES, source_id="83867", title="Андор",
                  original_title="Andor", synopsis="мой текст",
                  poster_url="/andor.jpg", year=2022, runtime=48,
                  released_at=date(2022, 9, 21),
                  seasons_count=2, episodes_count=24, synced_at=LATER),
        id=item_id,
    )


async def test_refresh_takes_only_the_asked_card(sessions):
    repository = LibraryRepository(sessions)
    mine = await repository.create(make_item(kind=Kind.SERIES, source_id="1"))
    other = await repository.create(
        make_item(kind=Kind.SERIES, source_id="2", seasons_count=5)
    )

    await repository.refresh_series_counts(mine, 2, 24, now=LATER)

    assert (await repository.get(other)).seasons_count == 5


async def test_refresh_keeps_my_data(sessions):
    """Перезагрузка карточки не должна сносить оценку, тег и закладку."""
    repository = LibraryRepository(sessions)
    item_id = await repository.create(make_item(kind=Kind.SERIES, source_id="1"))
    await RatingsRepository(sessions).set_score(item_id, 9.0, now=WHEN)
    tags = TagsRepository(sessions)
    await tags.assign(item_id, await tags.create(Kind.SERIES, "пересмотреть"))
    await WishlistRepository(sessions).add(item_id, now=WHEN)

    await repository.refresh_series_counts(item_id, 3, 30, now=LATER)

    assert (await RatingsRepository(sessions).get(item_id)).score == 9.0
    assert len(await tags.tags_of(item_id)) == 1
    assert await WishlistRepository(sessions).contains(item_id) is True


async def test_replace_fields_rewrites_everything_the_human_gave(sessions):
    """Сверяется карточка целиком: в форме правки человек меняет и дату
    выхода, и постер, и число серий — проверка по нескольким полям пропустила
    бы те, о которых забыли при записи."""
    repository = LibraryRepository(sessions)
    item_id = await repository.create(make_item(synopsis="старое", year=2014))

    written = make_item(
        kind=Kind.SERIES, title="Андор", original_title="Andor",
        synopsis="новое", year=2015, released_at=date(2022, 9, 21),
        poster_url="/andor.jpg", runtime=169,
        seasons_count=2, episodes_count=24, synced_at=LATER,
    )
    await repository.replace_fields(item_id, written)

    stored = await repository.get(item_id)
    # Источник и его номер не трогаются: это привязка, отдельная операция.
    assert stored == replace(
        written, id=item_id, source=Source.TMDB, source_id="157336"
    )


async def test_replace_fields_takes_only_the_asked_card(sessions):
    repository = LibraryRepository(sessions)
    mine = await repository.create(make_item(source_id="1"))
    other = await repository.create(make_item(source_id="2", title="соседняя"))

    await repository.replace_fields(mine, make_item(title="новое"))

    assert (await repository.get(other)).title == "соседняя"


async def test_replace_fields_does_not_move_identity(sessions):
    """Смена источника — это привязка, а не правка полей."""
    repository = LibraryRepository(sessions)
    item_id = await repository.create(make_item())

    await repository.replace_fields(
        item_id, make_item(source=Source.STEAM, source_id="999", title="другое")
    )

    stored = await repository.get(item_id)
    assert stored.source == Source.TMDB
    assert stored.source_id == "157336"
    assert stored.title == "другое"


async def test_emptying_a_field_by_hand_is_allowed(sessions):
    """Правка человеком может и стереть: пустое здесь — это значение."""
    repository = LibraryRepository(sessions)
    item_id = await repository.create(make_item(synopsis="было"))

    await repository.replace_fields(item_id, make_item(synopsis=""))

    assert (await repository.get(item_id)).synopsis == ""
