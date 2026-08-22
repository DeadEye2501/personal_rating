"""Треки альбома: порядок, перезапись целиком и уход вместе с карточкой."""

import pytest
from sqlalchemy import text

from backend.model import Kind
from backend.storage.repository.tracks import TracksRepository

SIDE_A = ["Bohemian Rhapsody", "Love of My Life", "'39"]


@pytest.fixture
def tracks(sessions):
    return TracksRepository(sessions)


async def test_tracks_come_back_in_the_order_they_were_written(tracks, card):
    """Порядок у альбома — часть данных, а не украшение: слушают его подряд.
    Наблюдается он списком, а не набором, и нарочно проверяется на именах, чей
    алфавитный порядок отличается от записанного, — иначе сортировку по
    названию было бы не отличить от сортировки по позиции."""
    album = await card(kind=Kind.MUSIC, title="A Night at the Opera")

    await tracks.replace(album, SIDE_A)

    assert await tracks.of(album) == SIDE_A


async def test_a_rewrite_replaces_the_whole_set(tracks, card):
    """Перезапись заменяет, а не доливает: человек убрал трек из списка —
    значит его там больше нет. Доливающая запись оставила бы удалённое
    навсегда, и убрать его стало бы нечем."""
    album = await card(kind=Kind.MUSIC, title="A Night at the Opera")
    await tracks.replace(album, SIDE_A)

    await tracks.replace(album, ["Love of My Life"])

    assert await tracks.of(album) == ["Love of My Life"]


async def test_a_card_without_tracks_answers_with_an_empty_list(tracks, card):
    """Пустой список — штатный ответ, а не отсутствие: треков нет ни у одного
    фильма, и спрашивают их за всю порцию ленты сразу."""
    film = await card(kind=Kind.MOVIE)

    assert await tracks.of(film) == []


async def test_tracks_leave_together_with_their_card(tracks, card, sessions, engine):
    """Осиротевший трек достался бы следующей карточке: `item` заведён без
    `AUTOINCREMENT`, и SQLite выдаёт номера повторно. Ровно так однажды чужая
    обложка досталась чужой карточке.

    Читается сырая таблица: `of` по несуществующей карточке и так отдаёт пустой
    список, и на нём уцелевшая строка была бы неотличима от убранной."""
    album = await card(kind=Kind.MUSIC, title="A Night at the Opera")
    await tracks.replace(album, SIDE_A)

    async with sessions() as session:
        await session.execute(text("DELETE FROM item WHERE id = :id"),
                              {"id": album})
        await session.commit()

    async with engine.connect() as connection:
        left = (await connection.execute(text("SELECT COUNT(*) FROM track"))
                ).scalar_one()

    assert left == 0
