import logging
from datetime import date

import pytest

from backend.model import (
    CompanyRole,
    Credit,
    ExternalId,
    ExternalRating,
    GenreSource,
    IdSource,
    Item,
    Kind,
    PersonRole,
    RatingSource,
    Source,
    SourceCard,
    new_manual_item,
)
from backend.service.linking import Linker, merge_fields, overwrite_fields
from backend.storage.repository.credits import companies, people
from backend.storage.repository.external import (
    ExternalIdsRepository,
    ExternalRatingsRepository,
)
from backend.storage.repository.genres import GenresRepository
from backend.storage.repository.library import ItemExists, LibraryRepository
from tests.backend.sources.conftest import responding
from tests.conftest import (
    LATER,
    MOMENT,
    POSTER,
    an_item,
    card_parts,
    film_genres,
    ours,
    picture,
)


def incoming(**overrides) -> SourceCard:
    fields = dict(
        item=an_item("157336", "Interstellar", year=2014, runtime=169,
                     synopsis="официальный синопсис",
                     poster_url="https://example.com/poster.jpg"),
        genre_ext_ids=((GenreSource.TMDB, "878"),),
        people=(Credit("Кристофер Нолан", PersonRole.DIRECTOR,
                       source=Source.TMDB, source_id="525"),),
        companies=(), external_ids=(), ratings=(),
    )
    fields.update(overrides)
    return SourceCard(**fields)


def mine(**fields) -> Item:
    """Ручная карточка как объект: слияние проверяется без базы."""
    return Item(id=1, kind=Kind.MOVIE, source=Source.MANUAL, source_id="u",
                title="Интерстеллар", synced_at=MOMENT, **fields)


def test_merge_keeps_what_the_human_typed():
    merged = merge_fields(mine(synopsis="мой текст"), incoming().item)

    assert merged.title == "Интерстеллар"
    assert merged.synopsis == "мой текст"


def test_merge_fills_only_the_empty():
    merged = merge_fields(mine(), incoming().item)

    assert merged.year == 2014
    assert merged.runtime == 169


FULL = an_item(
    "83867", "Andor", kind=Kind.SERIES, original_title="Andor",
    year=2022, released_at=date(2022, 9, 21), synopsis="официальный синопсис",
    poster_url="https://example.com/andor.jpg", runtime=48,
    seasons_count=2, episodes_count=24,
)


def test_every_field_a_source_may_fill_is_filled():
    """Все девять полей поимённо: проверка на трёх из них молчит, когда из набора
    выпадает четвёртое — а выпасть может любое, набор задан списком."""
    merged = merge_fields(mine(), FULL)

    assert (merged.title, merged.original_title) == ("Интерстеллар", "Andor")
    assert (merged.year, merged.released_at) == (2022, date(2022, 9, 21))
    assert merged.synopsis == "официальный синопсис"
    assert merged.poster_url == "https://example.com/andor.jpg"
    assert merged.runtime == 48
    assert (merged.seasons_count, merged.episodes_count) == (2, 24)


def test_merge_never_moves_identity_or_the_sync_mark():
    merged = merge_fields(mine(), incoming().item)

    assert (merged.id, merged.source, merged.source_id) == (1, Source.MANUAL, "u")
    assert merged.synced_at == MOMENT


def test_overwrite_takes_the_incoming_over_the_own():
    merged = overwrite_fields(mine(synopsis="набросок"), incoming().item)

    assert merged.title == "Interstellar"
    assert merged.synopsis == "официальный синопсис"


def test_overwrite_keeps_what_the_source_never_sent():
    """Разборщики кладут в непришедшее пустую строку, а не оставляют поле
    незаполненным: у TMDB на русском пустой синопсис — обычное дело, и написанный
    руками текст исчез бы безвозвратно."""
    empty = incoming(item=an_item("157336", "Interstellar")).item

    merged = overwrite_fields(mine(synopsis="мой текст", runtime=100), empty)

    assert merged.synopsis == "мой текст"
    assert merged.runtime == 100


@pytest.fixture
async def linker(sessions, engine, posters):
    await film_genres(engine)
    built = Linker(**card_parts(sessions, posters, responding(content=POSTER)))
    yield built
    await built.posters.aclose()


async def manual_card(sessions, **fields) -> int:
    return await LibraryRepository(sessions).create(
        new_manual_item(Kind.MOVIE, fields.pop("title", "Интерстеллар"),
                        synced_at=MOMENT, **fields)
    )


async def test_linking_moves_the_card_to_the_source(linker, sessions):
    item_id = await manual_card(sessions)

    await linker.link(item_id, incoming(), now=LATER)

    stored = await LibraryRepository(sessions).get(item_id)
    assert (stored.source, stored.source_id) == (Source.TMDB, "157336")
    assert stored.title == "Интерстеллар", "своё название затёрли"


async def test_linking_fills_the_gaps(linker, sessions):
    item_id = await manual_card(sessions)

    await linker.link(item_id, incoming(), now=LATER)

    stored = await LibraryRepository(sessions).get(item_id)
    assert stored.year == 2014
    assert stored.synopsis == "официальный синопсис"


@pytest.mark.parametrize("overwrite", [False, True])
async def test_linking_refreshes_the_sync_mark(linker, sessions, overwrite):
    """Иначе карточка, заведённая полгода назад, сразу окажется просроченной. С
    галочкой — то же: отметка источника не должна затирать момент привязки."""
    item_id = await manual_card(sessions)

    await linker.link(item_id, incoming(), now=LATER, overwrite=overwrite)

    assert (await LibraryRepository(sessions).get(item_id)).synced_at == LATER


async def test_the_type_of_the_card_is_never_changed(linker, sessions):
    """Тумблер стоял на фильмах, ссылка ведёт на сериал: тип карточки привязка не
    трогает. Что делать в этом случае, не решено — и пока не решено, менять тип
    молча нельзя."""
    item_id = await manual_card(sessions)

    await linker.link(item_id, incoming(item=an_item(
        "83867", "Andor", kind=Kind.SERIES, seasons_count=2,
    )), now=LATER)

    assert (await LibraryRepository(sessions).get(item_id)).kind is Kind.MOVIE


async def test_a_filled_cast_is_not_topped_up(linker, sessions):
    """Вписал одного разработчика — состав считается заполненным целиком."""
    item_id = await manual_card(sessions)
    ours = await people(sessions).create_manual("Мой режиссёр")
    await people(sessions).attach(item_id, ours, PersonRole.DIRECTOR)

    await linker.link(item_id, incoming(), now=LATER)

    names = [c.name for c in await people(sessions).credits_of(item_id)]
    assert names == ["Мой режиссёр"]


async def test_an_empty_cast_is_filled(linker, sessions):
    """Вместе с ролью и порядком в титрах: без порядка «топ-5 актёров»
    превращается в случайный список."""
    item_id = await manual_card(sessions)

    await linker.link(item_id, incoming(people=(
        Credit("Кристофер Нолан", PersonRole.DIRECTOR,
               source=Source.TMDB, source_id="525"),
        Credit("Мэттью Макконахи", PersonRole.ACTOR, position=0,
               source=Source.TMDB, source_id="10297"),
    )), now=LATER)

    found = await people(sessions).credits_of(item_id)
    assert {(c.name, c.role, c.position) for c in found} == {
        ("Кристофер Нолан", PersonRole.DIRECTOR, None),
        ("Мэттью Макконахи", PersonRole.ACTOR, 0),
    }


async def test_a_chosen_genre_is_not_topped_up(linker, sessions):
    """Источник даёт свой жанр, отличный от выбранного руками. С пустым
    `genre_ext_ids` дополнять было бы нечем по построению, и проверка прошла бы
    даже у реализации, которая молча затирает выбранное человеком."""
    item_id = await manual_card(sessions)
    await GenresRepository(sessions).set_for_item(item_id, [1])

    await linker.link(item_id, incoming(genre_ext_ids=((GenreSource.TMDB, "12"),)),
                      now=LATER)

    names = [g.name for g in await GenresRepository(sessions).genres_of(item_id)]
    assert names == ["фантастика"]


async def test_an_empty_genre_set_is_filled(linker, sessions):
    item_id = await manual_card(sessions)

    await linker.link(item_id, incoming(), now=LATER)

    names = [g.name for g in await GenresRepository(sessions).genres_of(item_id)]
    assert names == ["фантастика"]


async def test_overwrite_takes_everything_the_source_gave(linker, sessions):
    """На случай, когда карточка заводилась на скорую руку."""
    item_id = await manual_card(sessions, synopsis="набросок")
    ours = await people(sessions).create_manual("Мой режиссёр")
    await people(sessions).attach(item_id, ours, PersonRole.DIRECTOR)

    await linker.link(item_id, incoming(), now=LATER, overwrite=True)

    stored = await LibraryRepository(sessions).get(item_id)
    assert (stored.title, stored.synopsis) == ("Interstellar",
                                               "официальный синопсис")
    names = [c.name for c in await people(sessions).credits_of(item_id)]
    assert names == ["Кристофер Нолан"]


async def test_overwrite_does_not_wipe_what_the_source_never_had(linker, sessions):
    """У игр состав заполняется только руками: ни Steam, ни GOG людей не отдают.
    Стереть его перезаписью — значит потерять безвозвратно."""
    item_id = await manual_card(sessions)
    ours = await people(sessions).create_manual("Мой режиссёр")
    await people(sessions).attach(item_id, ours, PersonRole.DIRECTOR)
    studio = await companies(sessions).create("Моя студия")
    await companies(sessions).attach(item_id, studio, CompanyRole.DEVELOPER)

    await linker.link(item_id, incoming(people=(), companies=()), now=LATER,
                      overwrite=True)

    assert [c.name for c in await people(sessions).credits_of(item_id)] == [
        "Мой режиссёр"
    ]
    assert [c.name for c in await companies(sessions).credits_of(item_id)] == [
        "Моя студия"
    ]


async def test_overwrite_does_not_wipe_genres_the_source_never_had(linker, sessions):
    item_id = await manual_card(sessions)
    await GenresRepository(sessions).set_for_item(item_id, [1])

    await linker.link(item_id, incoming(genre_ext_ids=()), now=LATER,
                      overwrite=True)

    names = [g.name for g in await GenresRepository(sessions).genres_of(item_id)]
    assert names == ["фантастика"]


async def test_overwrite_does_replace_the_genres_the_source_gave(linker, sessions):
    """Обратная сторона предыдущего: с галочкой приехавшее побеждает. Без этой
    проверки пара выше проходит и у реализации, которая жанры не трогает вовсе."""
    item_id = await manual_card(sessions)
    await GenresRepository(sessions).set_for_item(item_id, [1])

    await linker.link(item_id, incoming(genre_ext_ids=((GenreSource.TMDB, "12"),)),
                      now=LATER, overwrite=True)

    names = [g.name for g in await GenresRepository(sessions).genres_of(item_id)]
    assert names == ["приключения"]


async def test_identifiers_and_ratings_arrive_with_the_link(linker, sessions):
    """Привязка — это ещё и то, чем карточка известна чужим базам."""
    item_id = await manual_card(sessions)

    await linker.link(item_id, incoming(
        external_ids=(ExternalId(IdSource.IMDB, "tt0816692"),),
        ratings=(ExternalRating(RatingSource.TMDB, 8.4, MOMENT),),
    ), now=LATER)

    ids = await ExternalIdsRepository(sessions).ids_of(item_id)
    ratings = await ExternalRatingsRepository(sessions).ratings_of(item_id)
    assert [(i.source, i.value) for i in ids] == [(IdSource.IMDB, "tt0816692")]
    assert [(r.source, r.value) for r in ratings] == [(RatingSource.TMDB, 8.4)]


async def test_linking_to_an_occupied_identity_is_refused(linker, sessions):
    library = LibraryRepository(sessions)
    await library.create(
        an_item("157336", "уже есть")
    )
    ours = await manual_card(sessions, title="мой дубль")

    with pytest.raises(ItemExists):
        await linker.link(ours, incoming(), now=LATER)

    assert (await library.get(ours)).source is Source.MANUAL


async def test_an_identifier_taken_by_another_card_stops_everything(linker, sessions):
    """Занятый чужой карточкой IMDb ID всплыл бы только на записи —
    то есть после того, как источник уже переставлен, а поля уже слиты.
    Карточка осталась бы привязанной наполовину."""
    taken = ExternalId(IdSource.IMDB, "tt0816692")
    other = await manual_card(sessions, title="чужая")
    await ExternalIdsRepository(sessions).put(other, taken)
    ours = await manual_card(sessions, title="моя")

    with pytest.raises(ItemExists):
        await linker.link(ours, incoming(external_ids=(taken,)), now=LATER)

    stored = await LibraryRepository(sessions).get(ours)
    assert stored.source is Source.MANUAL
    assert stored.year is None, "поля слиты, хотя привязка не состоялась"


async def test_an_identifier_of_this_very_card_is_not_in_the_way(linker, sessions):
    """Тот же идентификатор на той же карточке — обычное дело: привязку повторяют
    после правки, и своё занятым не считается."""
    taken = ExternalId(IdSource.IMDB, "tt0816692")
    item_id = await manual_card(sessions)
    await ExternalIdsRepository(sessions).put(item_id, taken)

    await linker.link(item_id, incoming(external_ids=(taken,)), now=LATER)

    assert (await LibraryRepository(sessions).get(item_id)).source is Source.TMDB


async def test_a_manual_card_gets_its_poster_on_linking(linker, sessions):
    item_id = await manual_card(sessions)

    await linker.link(item_id, incoming(), now=LATER)

    assert await linker.posters._store.get(item_id) == POSTER


async def test_an_own_poster_is_not_replaced(linker, sessions):
    """Обложка — такое же поле: непустое значит занятое."""
    item_id = await manual_card(sessions)
    await linker.posters.store_upload(item_id, picture(400, 400), now=MOMENT)
    ours = await linker.posters._store.get(item_id)

    await linker.link(item_id, incoming(), now=LATER)

    assert await linker.posters._store.get(item_id) == ours


async def test_overwrite_replaces_the_own_poster(linker, sessions):
    """Обратная сторона: с галочкой приезжает обложка источника."""
    item_id = await manual_card(sessions)
    await linker.posters.store_upload(item_id, picture(400, 400), now=MOMENT)

    await linker.link(item_id, incoming(), now=LATER, overwrite=True)

    assert await linker.posters._store.get(item_id) == POSTER


async def test_a_refused_poster_leaves_the_link_in_place(sessions, engine, posters,
                                                        caplog):
    """CDN молчит — привязка всё равно состоялась: строка уже есть, данные уже
    свои, откатывать нечего. Отказ уходит в лог, иначе пропажа обложки не
    оставляет следа вовсе."""
    await film_genres(engine)
    linker = Linker(**card_parts(sessions, posters, responding(500, content=POSTER)))
    item_id = await manual_card(sessions)

    with caplog.at_level(logging.WARNING):
        await linker.link(item_id, incoming(), now=LATER)

    assert (await LibraryRepository(sessions).get(item_id)).source is Source.TMDB
    assert not await linker.posters._store.has(item_id)
    assert [message for message in ours(caplog) if "обложка" in message]
    await linker.posters.aclose()


async def test_a_card_without_a_poster_url_keeps_its_own(linker, sessions):
    """Источник обложки не дал — стирать свою нечем и незачем."""
    item_id = await manual_card(sessions)
    await linker.posters.store_upload(item_id, picture(400, 400), now=MOMENT)
    ours = await linker.posters._store.get(item_id)

    await linker.link(item_id, incoming(item=an_item(
        "157336", "Interstellar",
    )), now=LATER, overwrite=True)

    assert await linker.posters._store.get(item_id) == ours
