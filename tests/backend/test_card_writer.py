"""Запись карточки источника в базу целиком — или ничего."""

import asyncio
import sqlite3

import pytest

from backend.model import (
    CompanyRole,
    Credit,
    ExternalId,
    ExternalRating,
    GenreSource,
    IdSource,
    Kind,
    PersonRole,
    RatingSource,
    Reason,
    Refusal,
    Source,
    SourceCard,
)
from backend.service.cards import CardWriter
from backend.storage.repository.credits import companies, people
from backend.storage.repository.external import (
    ExternalIdsRepository,
    ExternalRatingsRepository,
)
from backend.storage.repository.genres import GenresRepository
from backend.storage.repository.library import LibraryRepository
from backend.storage.repository.tracks import TracksRepository
from tests.conftest import MOMENT as WHEN
from tests.conftest import (
    POSTER,
    album_card,
    an_item,
    card_parts,
    film_genres,
    picture,
    responding,
    seed,
)


def source_card(**overrides) -> SourceCard:
    fields = dict(
        item=an_item("157336", "Интерстеллар", year=2014, runtime=169,
                     poster_url="https://example.com/poster.jpg"),
        genre_ext_ids=((GenreSource.TMDB, "878"), (GenreSource.TMDB, "12")),
        people=(
            Credit("Кристофер Нолан", PersonRole.DIRECTOR,
                   source=Source.TMDB, source_id="525"),
            Credit("Мэттью Макконахи", PersonRole.ACTOR, position=0,
                   source=Source.TMDB, source_id="10297"),
        ),
        companies=(),
        external_ids=(ExternalId(IdSource.IMDB, "tt0816692"),),
        ratings=(ExternalRating(RatingSource.TMDB, 8.4, WHEN),),
    )
    fields.update(overrides)
    return SourceCard(**fields)


def game_card(source_id: str = "292030", **overrides) -> SourceCard:
    """Игра: жанры и оценки к делу не идут, а студия приходит голой строкой."""
    return source_card(**{
        "item": an_item(source_id, f"игра {source_id}", kind=Kind.GAME,
                        source=Source.STEAM,
                        poster_url="https://example.com/p.jpg"),
        "genre_ext_ids": (), "people": (), "external_ids": (), "ratings": (),
        "companies": (Credit("CD Projekt RED", CompanyRole.DEVELOPER),),
        **overrides,
    })


def another_movie(source_id: str, **overrides) -> SourceCard:
    """Вторая карточка того же вида: её идентичность свободна, а состав задаёт
    тест."""
    return source_card(**{
        "item": an_item(source_id, f"фильм {source_id}",
                        poster_url="https://example.com/p.jpg"),
        "external_ids": (),
        **overrides,
    })


async def build(sessions, engine, posters, transport=None) -> CardWriter:
    """Писатель со всеми репозиториями поверх тестовой базы. Транспорт задаётся
    там, где обложка должна не приехать.

    Справочник жанров кладётся руками: в базе из объявлений он пуст, а разрешение
    чужих идентификаторов идёт через него."""
    await film_genres(engine)
    return CardWriter(**card_parts(sessions, posters,
                                   transport or responding(content=POSTER)))


@pytest.fixture
async def writer(sessions, engine, posters):
    built = await build(sessions, engine, posters)
    yield built
    await built.posters.aclose()


async def test_a_whole_card_lands_in_the_database(writer, sessions):
    item_id = await writer.save(source_card(), POSTER)
    assert isinstance(item_id, int)

    stored = await LibraryRepository(sessions).get(item_id)
    assert stored.title == "Интерстеллар"
    assert stored.runtime == 169
    assert stored.year == 2014


async def test_genres_are_resolved_through_the_reference(writer, sessions):
    item_id = await writer.save(source_card(), POSTER)

    names = {g.name for g in await GenresRepository(sessions).genres_of(item_id)}
    assert names == {"фантастика", "приключения"}


async def test_people_are_attached_with_their_roles(writer, sessions):
    """Роль привязана к человеку, а не лежит рядом набором: перепутанные
    местами режиссёр и актёр набор имён не различает."""
    item_id = await writer.save(source_card(), POSTER)

    found = await people(sessions).credits_of(item_id)
    assert {(c.name, c.role, c.position) for c in found} == {
        ("Кристофер Нолан", PersonRole.DIRECTOR, None),
        # Порядок в титрах — это «топ-5 актёров»: потерянный, он превращает
        # список в случайный.
        ("Мэттью Макконахи", PersonRole.ACTOR, 0),
    }


async def test_the_same_person_on_two_cards_is_one_row(writer, sessions):
    """Склейка по идентификатору источника: иначе «показать всё с этим
    человеком» разваливается на пять Кристоферов Ноланов."""
    first = await writer.save(source_card(), POSTER)
    second = await writer.save(another_movie("374720"), POSTER)

    assert len(await people(sessions).find_by_name("Кристофер Нолан")) == 1
    for item_id in (first, second):
        names = [c.name for c in await people(sessions).credits_of(item_id)]
        assert "Кристофер Нолан" in names, "одна строка — но привязана к обеим"


async def test_two_namesakes_from_the_source_do_not_merge(writer, sessions):
    """Два разных актёра с одним именем не должны стать одной строкой — человек
    в импорте не участвует и заметить подмену не может."""
    item_id = await writer.save(source_card(people=(
        Credit("Василий Пупкин", PersonRole.ACTOR, position=0,
               source=Source.TMDB, source_id="1"),
        Credit("Василий Пупкин", PersonRole.ACTOR, position=1,
               source=Source.TMDB, source_id="2"),
    )), POSTER)

    assert len(await people(sessions).find_by_name("Василий Пупкин")) == 2
    assert len(await people(sessions).credits_of(item_id)) == 2


async def test_studios_without_identity_are_merged_by_name(writer, sessions):
    """У Steam и GOG студии приходят голыми строками — склеивать их больше не по
    чему, и это законно."""
    for source_id in ("1", "2"):
        await writer.save(game_card(source_id), POSTER)

    assert len(await companies(sessions).find_by_name("CD Projekt RED")) == 1


async def test_companies_are_written_for_a_game(writer, sessions):
    item_id = await writer.save(game_card(), POSTER)

    found = await companies(sessions).credits_of(item_id)
    assert [(c.name, c.role) for c in found] == [
        ("CD Projekt RED", CompanyRole.DEVELOPER)
    ]


async def test_people_and_studios_do_not_land_in_one_another(writer, sessions):
    """Репозитория два, и таблицы у них разные: слитые, они показали бы студию
    в списке людей."""
    movie = await writer.save(source_card(), POSTER)
    game = await writer.save(game_card(), POSTER)

    assert await companies(sessions).credits_of(movie) == []
    assert await people(sessions).credits_of(game) == []


async def test_external_identifiers_and_ratings_are_written(writer, sessions):
    item_id = await writer.save(source_card(), POSTER)

    ids = await ExternalIdsRepository(sessions).ids_of(item_id)
    ratings = await ExternalRatingsRepository(sessions).ratings_of(item_id)
    assert [(i.source, i.value) for i in ids] == [(IdSource.IMDB, "tt0816692")]
    # Со значением и отметкой времени, а не только с источником: на них стоят
    # три состояния external_rating и сроки годности. Проверка одного лишь
    # источника пропустила бы запись нуля, None или чужого числа.
    assert [(r.source, r.value) for r in ratings] == [(RatingSource.TMDB, 8.4)]
    assert ratings[0].fetched_at == WHEN


async def test_the_poster_is_stored(writer):
    item_id = await writer.save(source_card(), POSTER)

    assert await writer.posters._store.get(item_id) == POSTER


async def test_a_prefetched_poster_is_not_downloaded_again(writer):
    """Круги 2а и 2б можно пустить параллельно — оркестратор передаст байты."""
    ready = picture(600, 900)

    item_id = await writer.save(source_card(), ready)

    assert await writer.posters._store.get(item_id) == ready


async def test_a_card_without_a_cover_is_still_written(writer):
    """Обложки нет — ни в самом источнике, ни по угаданному адресу Steam. Такая
    карточка пишется целиком, только без картинки: добывать её пробовал
    загрузчик, и это его ответ, а не «мы не пробовали»."""
    item_id = await writer.save(source_card(
        item=an_item("1", "Без обложки"),
        external_ids=(),
    ), None)

    assert isinstance(item_id, int)
    assert not await writer.posters._store.has(item_id)


async def test_a_taken_identifier_leaves_nothing_behind(writer, sessions):
    """Занятый IMDb ID срывает запись на середине — убираем за собой. Проверка
    не только карточки: за ней остались бы и жанры, и люди, и постер."""
    await writer.save(source_card(), POSTER)

    result = await writer.save(another_movie(
        "999", external_ids=(ExternalId(IdSource.IMDB, "tt0816692"),),
    ), POSTER)

    assert isinstance(result, Refusal)
    # Отказ назван источником карточки и причиной «ответил непонятно чем»: по ним
    # наверху решают, показывать человеку строку или ждать.
    assert (result.source, result.reason) == ("tmdb", Reason.BROKEN)
    dropped = await LibraryRepository(sessions).find_by_source(Kind.MOVIE, Source.TMDB, "999")
    assert dropped is None


async def test_the_rollback_takes_the_written_half_with_it(writer, sessions):
    """До занятого идентификатора успевают лечь жанры и люди. Уходят они
    каскадом, а каскад — свойство схемы: без внешнего ключа с `ON DELETE CASCADE`
    строки остались бы висеть на номере, который достанется другой карточке."""
    first = await writer.save(source_card(), POSTER)
    half_written = first + 1

    await writer.save(another_movie(
        "999", external_ids=(ExternalId(IdSource.IMDB, "tt0816692"),),
    ), POSTER)

    # Идентификаторы и оценки не проверяются: срыв наступает на первом же
    # `_ids.put`, до него их не записано, и пустота истинна по построению.
    assert await GenresRepository(sessions).genres_of(half_written) == []
    assert await people(sessions).credits_of(half_written) == []


async def test_the_rollback_takes_the_poster_with_it(writer, monkeypatch):
    """Постер лежит во втором файле базы, и каскадом он не уходит: оставленный,
    он достался бы следующей карточке с этим же номером.

    Срыв наводится после того, как обложка легла, — иначе проверять было бы
    нечего: постер пишется последним шагом, и занятый идентификатор до него не
    доходит вовсе."""
    stored: list[int] = []
    save = writer.posters.save

    async def save_then_break(item_id, data, now):
        await save(item_id, data, now)
        stored.append(item_id)
        raise OSError("второй файл базы отвалился после записи")

    monkeypatch.setattr(writer.posters, "save", save_then_break)

    result = await writer.save(source_card(), POSTER)

    assert isinstance(result, Refusal)
    assert stored, "обложка до хранилища не дошла — тест проверяет не то"
    assert await writer.posters._store.has(stored[0]) is False, \
        "постер откаченной карточки остался и достанется следующей"


async def test_the_writer_clears_the_place_under_the_cover_too(writer,
                                                               monkeypatch):
    """Уборка чужой обложки на этом номере — общая у обоих путей заведения, и
    писатель обязан идти тем же путём, что и ручная карточка: `id` SQLite выдаёт
    повторно, а обложка лежит во втором файле базы без внешних ключей.

    Наблюдается вызовом, а не следствием: у писателя обложка пишется своим
    последним шагом, и следствие уборки он затирает сам."""
    cleared: list[int] = []

    async def note(item_id):
        cleared.append(item_id)

    monkeypatch.setattr(writer.posters, "delete", note)

    item_id = await writer.save(source_card(), POSTER)

    assert cleared == [item_id], "писатель завёл строку мимо общей уборки"


async def test_the_rollback_undoes_a_failed_clearing(writer, sessions,
                                                     monkeypatch):
    """Уборка — второй заход в базу после закоммиченной строки, и сорваться он
    может: занятый файл хранилища, отмена при закрытии окна. Без отката осталась
    бы строка со свежим `synced_at`, без жанров, состава и обложки, — та самая
    частичная карточка, которой «не бывает», и перезапроса у неё не будет
    никогда."""
    async def refuse(item_id):
        raise OSError("хранилище занято")

    monkeypatch.setattr(writer.posters, "delete", refuse)

    result = await writer.save(source_card(), POSTER)

    assert isinstance(result, Refusal), "наружу из писателя летит отказ"
    assert await LibraryRepository(sessions).find_by_source(
        Kind.MOVIE, Source.TMDB, "157336"
    ) is None, "строка осталась без обложки, состава и жанров"


async def test_cancelling_the_write_takes_the_card_with_it(writer, sessions,
                                                           monkeypatch):
    """Отмена — не поломка, а штатный путь: так гасится загрузка при закрытии
    окна. В `except Exception` она не попадает, потому что наследник
    `BaseException`, и без своей ветки в базе осталась бы карточка со свежим
    `synced_at`, который утверждает, что она полная, — перезапроса не будет
    никогда. Гасим на записи идентификаторов: к этому моменту уже легли и жанры,
    и люди, то есть уходит именно записанная половина.

    Наружу отмена уходит отменой: превратить её в отказ значит соврать про
    закрытие приложения."""
    async def cancel(*_args, **_kwargs):
        raise asyncio.CancelledError

    monkeypatch.setattr(writer._ids, "put", cancel)

    with pytest.raises(asyncio.CancelledError):
        await writer.save(source_card(), POSTER)

    assert await LibraryRepository(sessions).find_by_source(
        Kind.MOVIE, Source.TMDB, "157336") is None


async def test_a_taken_card_identity_is_a_refusal_not_an_exception(writer):
    """Контракт save — int или Refusal, исключений наружу не летит. Отказ назван
    источником карточки: их шесть, и по имени наверху понимают, кто отказал."""
    await writer.save(source_card(), POSTER)

    result = await writer.save(source_card(external_ids=()), POSTER)

    assert isinstance(result, Refusal)
    assert (result.source, result.reason) == ("tmdb", Reason.BROKEN)


async def test_an_unknown_genre_does_not_stop_the_card(writer, sessions):
    """Источник добавил жанр, которого в миграции нет: карточка показывается без
    него, и всё — незнакомое молча отбрасывается."""
    item_id = await writer.save(source_card(genre_ext_ids=(
        (GenreSource.TMDB, "878"), (GenreSource.TMDB, "99999"),
    )), POSTER)

    names = {g.name for g in await GenresRepository(sessions).genres_of(item_id)}
    assert names == {"фантастика"}


async def test_the_marks_of_a_card_are_read_by_the_rules_of_its_source(
    writer, sessions, engine
):
    """Метка сама по себе жанра не означает: `9` у Steam даёт «Гонки» только
    без `1662`. Правило, а не строка соответствия, — и до записи карточки
    доезжает именно его ответ."""
    await seed(
        engine,
        "INSERT INTO genre (id, name, kind) VALUES "
        "(10, 'Racing', 'game'), (11, 'Survival', 'game')",
        "INSERT INTO genre_rule (id, source, genre_id, alone) VALUES "
        "(20, 'steam', 10, 0), (21, 'steam', 11, 0)",
        "INSERT INTO genre_rule_mark (rule_id, ext_id, forbidden) VALUES "
        "(20, '9', 0), (20, '1662', 1), (21, '1662', 0)",
    )

    item_id = await writer.save(game_card(genre_ext_ids=(
        (GenreSource.STEAM, "9"), (GenreSource.STEAM, "1662"),
    )), POSTER)

    names = {g.name for g in await GenresRepository(sessions).genres_of(item_id)}
    assert names == {"Survival"}


async def test_the_poster_is_dated_by_the_moment_of_the_card(writer, tmp_path):
    """Отметка постера — момент синхронизации карточки, а не «сейчас»: по ней
    потом решают, не пора ли обновить, и разъехавшись с карточкой она соврёт.

    Читается файл, а не хранилище: наружу `PosterStore` отдаёт байты, отметку он
    не показывает никому — сегодня её никто и не спрашивает."""
    item_id = await writer.save(source_card(), POSTER)
    await writer.posters.aclose()

    connection = sqlite3.connect(tmp_path / "posters.db")
    try:
        stored = connection.execute(
            "SELECT fetched_at FROM poster WHERE item_id = ?", (item_id,)
        ).fetchone()
    finally:
        connection.close()

    assert stored[0].startswith(WHEN.isoformat(sep=" "))


async def test_an_album_from_the_source_keeps_its_tracks(writer, sessions):
    """Частичной карточки из внешнего источника в базе не бывает, и треки —
    такая же её часть, как состав. Альбом, записанный без них, выглядит целым:
    `synced_at` у него свежий, то есть перезапроса не случилось бы никогда."""
    item_id = await writer.save(album_card(), POSTER)

    assert isinstance(item_id, int)
    assert await TracksRepository(sessions).of(item_id) == [
        "Группа крови", "Закрой за мной дверь"]


async def test_a_broken_write_takes_the_tracks_with_it(writer, sessions,
                                                       monkeypatch):
    """Осиротевший трек достался бы следующей карточке с тем же номером: `item`
    заведён без `AUTOINCREMENT`, и однажды так досталась чужая обложка.

    Чинить тут нечего — `track` объявлен через `item_fk` с `ondelete="CASCADE"`,
    и уборка карточки уносит треки сама. Тест сторожит, что каскад останется на
    месте, а не проверяет свой код: срыв наводится **после** записи треков,
    иначе проверять было бы нечего."""
    written: list[int] = []
    save = writer.posters.save

    async def save_then_break(item_id, data, now):
        await save(item_id, data, now)
        written.append(item_id)
        raise OSError("второй файл базы отвалился после записи")

    monkeypatch.setattr(writer.posters, "save", save_then_break)

    result = await writer.save(album_card(), POSTER)

    assert isinstance(result, Refusal)
    assert written, "до обложки дело не дошло — тест проверяет не то"
    assert await TracksRepository(sessions).of(written[0]) == [], \
        "треки откаченной карточки остались и достанутся следующей"
