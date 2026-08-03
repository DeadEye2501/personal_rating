"""Приведение хранимых оценок к настроенной шкале."""

import pytest
from sqlalchemy import text

from backend.app import build_backend
from backend.config import load_config
from backend.model import Filters, Kind, Source
from backend.storage.repository.ratings import RatingsRepository
from backend.storage import rescale
from backend.storage.rescale import apply_scale, rescaled
from backend.storage.session import create_engine, session_factory
from backend.storage.tables import metadata
from tests.conftest import MOMENT, rated, unreachable


async def game_with_aspects(sessions, visual, narrative, gameplay) -> int:
    """Игра с тремя проставленными сторонами. Оценка при заведении не ставится:
    у игры она не выставляется, а считается из сторон."""
    item_id = await rated(sessions, "292030", None, kind=Kind.GAME,
                          source=Source.STEAM)
    await RatingsRepository(sessions).set_aspects(
        item_id, visual, narrative, gameplay, MOMENT)
    return item_id


async def stored_mark(sessions) -> int:
    async with sessions() as session:
        return (await session.execute(text("PRAGMA user_version"))).scalar_one()


@pytest.mark.parametrize(("value", "expected"), [
    (10, 5), (9, 5), (8, 4), (7, 4), (6, 3), (5, 3), (4, 2), (3, 2), (2, 1),
    (1, 1), (None, None),
])
def test_ten_becomes_five(value, expected):
    assert rescaled(value, 5) == expected


@pytest.mark.parametrize(("value", "expected"), [
    (5, 10), (4, 8), (3, 6), (2, 4), (1, 2), (None, None),
])
def test_five_becomes_ten(value, expected):
    assert rescaled(value, 10) == expected


async def test_a_score_is_converted(sessions):
    """Оценка кино пересчитывается по таблице из спеки."""
    item_id = await rated(sessions, "157336", 9.0)

    await apply_scale(sessions, 5)

    assert (await RatingsRepository(sessions).get(item_id)).score == 5


async def test_the_game_average_is_rebuilt_from_its_sides(sessions):
    """Средняя игры собирается из пересчитанных сторон, а не пересчитывается
    сама: 7, 8, 9 дают 8.0, и по таблице это 4, тогда как из 4, 4, 5 выходит
    4.33. Верна вторая — иначе оценка игры разошлась бы со своими же сторонами,
    показанными рядом в той же карточке."""
    item_id = await game_with_aspects(sessions, 7, 8, 9)

    await apply_scale(sessions, 5)

    got = await RatingsRepository(sessions).get(item_id)
    assert (got.visual, got.narrative, got.gameplay) == (4, 4, 5)
    assert got.score == pytest.approx(13 / 3)


async def test_a_second_start_changes_nothing(sessions):
    """Отметка не даёт делить пополам на каждом запуске: иначе при `SCALE_X2=0`
    пятёрка уезжала бы в 3, потом в 2, потом в 1."""
    item_id = await rated(sessions, "157336", 9.0)

    await apply_scale(sessions, 5)
    await apply_scale(sessions, 5)

    assert (await RatingsRepository(sessions).get(item_id)).score == 5


async def test_an_unmarked_base_is_already_on_ten(sessions):
    """Нулевая отметка — это база старше настройки, и оценки в ней уже
    десятибалльные. Приняв ноль за «неизвестно» и пересчитав, мы удвоили бы всю
    библиотеку при первом же запуске новой версии — молча и необратимо."""
    item_id = await rated(sessions, "157336", 9.0)

    await apply_scale(sessions, 10)

    assert (await RatingsRepository(sessions).get(item_id)).score == 9


async def test_the_mark_and_the_scores_move_together(sessions):
    """Отметка ставится той же транзакцией, что и оценки: иначе оборванный
    пересчёт оставил бы половину переведённой библиотеки под отметкой, которая
    утверждает, что переведена вся."""
    await rated(sessions, "157336", 9.0)

    await apply_scale(sessions, 5)

    assert await stored_mark(sessions) == 5


async def built_on(tmp_path, scale: str):
    """Собранный бэкенд на базе, которая уже лежит в этой папке. Схема здесь
    руками: миграции — отдельный процесс, а предмет проверки — сборка."""
    config = load_config({"DATA_DIR": str(tmp_path), "SCALE_X2": scale},
                         base_dir=tmp_path)
    return await build_backend(config, transport=unreachable())


async def test_the_built_backend_converts_and_carries_the_scale(tmp_path):
    """Три звена проводки стоят в сборке, и каждое снималось бы молча: на
    свежей базе пересчитывать нечего, а шкалу по умолчанию не отличить от
    настроенной.

    Проверяется всё, что видно снаружи от одной настройки: оценка переведена,
    число ступеней отдано наружу, столбцов у гистограммы столько же."""
    engine = create_engine(tmp_path / "library.db")
    async with engine.begin() as connection:
        await connection.run_sync(metadata.create_all)
    item_id = await rated(session_factory(engine), "157336", 9.0)
    await engine.dispose()

    backend = await built_on(tmp_path, "0")
    try:
        histogram = await backend.feed.histogram(Kind.MOVIE, Filters())

        assert (await backend.ratings.get(item_id)).score == 5
        assert backend.scale == 5
        assert [b.score for b in histogram.buckets] == [1, 2, 3, 4, 5]
    finally:
        await backend.aclose()


async def test_a_card_without_a_score_survives_the_pass(sessions):
    """Пустая оценка остаётся пустой, а не становится нулём: карточка списка дел
    живёт без оценки, и приехавший ноль показал бы её оценённой."""
    item_id = await rated(sessions, "157336", None)
    await RatingsRepository(sessions).set_review(item_id, "потом", MOMENT)

    await apply_scale(sessions, 5)

    got = await RatingsRepository(sessions).get(item_id)
    assert got.score is None
    assert got.review == "потом"


async def test_a_broken_pass_leaves_neither_scores_nor_the_mark(sessions,
                                                                monkeypatch):
    """Оборванный пересчёт откатывается целиком.

    Иначе половина библиотеки осталась бы переведённой под отметкой, которая
    обещает всю, — и второй запуск, увидев отметку, не тронул бы вторую
    половину никогда."""
    first = await rated(sessions, "157336", 9.0)
    await rated(sessions, "27205", 8.0)
    moved = rescale._moved
    done = []

    def failing(row, scale):
        done.append(row)
        if len(done) > 1:
            raise RuntimeError("оборвалось на середине")
        return moved(row, scale)

    monkeypatch.setattr(rescale, "_moved", failing)

    with pytest.raises(RuntimeError):
        await apply_scale(sessions, 5)

    assert (await RatingsRepository(sessions).get(first)).score == 9
    assert await stored_mark(sessions) == 0
