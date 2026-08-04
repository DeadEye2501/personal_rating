"""Своя оценка карточки и её пересчёт."""

from datetime import timedelta

import pytest
from sqlalchemy import select

from backend.model import Kind
from backend.storage.repository.library import LibraryRepository
from backend.storage.repository.ratings import RatingsRepository
from backend.storage.tables import rating as rating_table
from tests.conftest import LATER, MOMENT as WHEN


async def test_score_of_a_film_is_what_was_set(sessions, card):
    item_id = await card()
    repository = RatingsRepository(sessions)
    await repository.set_score(item_id, 8.0, now=WHEN)

    stored = await repository.get(item_id)
    assert stored.score == 8.0
    # Отзыва не писали — колонка пуста, и наружу это пустая строка, а не None:
    # иначе в поле рецензии показалось бы слово «None».
    assert stored.review == ""


async def test_aspects_recompute_the_score(sessions, card):
    item_id = await card(Kind.GAME)
    repository = RatingsRepository(sessions)
    score = await repository.set_aspects(item_id, 8, 7, 7, now=WHEN)
    assert score == pytest.approx(7.3333, abs=1e-4)
    assert (await repository.get(item_id)).score == pytest.approx(7.3333, abs=1e-4)


async def test_aspects_are_stored_each_in_its_own_column(sessions, card):
    """Три шкалы — три колонки, и перепутанные местами дали бы то же среднее."""
    item_id = await card(Kind.GAME)
    repository = RatingsRepository(sessions)
    await repository.set_aspects(item_id, 9, 5, 1, now=WHEN)

    stored = await repository.get(item_id)
    assert (stored.visual, stored.narrative, stored.gameplay) == (9, 5, 1)


async def test_unset_aspect_does_not_drag_the_score_down(sessions, card):
    item_id = await card(Kind.GAME)
    repository = RatingsRepository(sessions)
    score = await repository.set_aspects(item_id, 8, None, 6, now=WHEN)
    assert score == 7.0


async def test_clearing_all_aspects_leaves_no_score(sessions, card):
    item_id = await card(Kind.GAME)
    repository = RatingsRepository(sessions)
    await repository.set_aspects(item_id, 8, 7, 7, now=WHEN)
    score = await repository.set_aspects(item_id, None, None, None, now=LATER)
    assert score is None
    assert (await repository.get(item_id)).score is None


async def test_the_first_write_stamps_both_times_with_now(sessions, engine, card):
    """Оба времени у первой оценки — момент записи. Проверять их только после
    второй записи мало: там `updated_at` уже переписан, и неверное значение при
    вставке не увидеть."""
    item_id = await card()
    await RatingsRepository(sessions).set_score(item_id, 8.0, now=WHEN)

    async with engine.connect() as connection:
        row = (await connection.execute(
            select(rating_table.c.created_at, rating_table.c.updated_at)
            .where(rating_table.c.item_id == item_id)
        )).one()
    assert (row.created_at, row.updated_at) == (WHEN, WHEN)


async def test_second_write_updates_and_keeps_created_at(sessions, engine, card):
    item_id = await card()
    repository = RatingsRepository(sessions)
    await repository.set_score(item_id, 6.0, now=WHEN)
    await repository.set_score(item_id, 9.0, now=LATER)

    # Читаем типизированными колонками, а не text(): у сырого SQL нет сведений
    # о типах, и DateTime вернулся бы строкой.
    async with engine.connect() as connection:
        row = (await connection.execute(
            select(rating_table.c.score,
                   rating_table.c.created_at,
                   rating_table.c.updated_at)
            .where(rating_table.c.item_id == item_id)
        )).one()
    assert row.score == 9.0
    assert row.created_at == WHEN
    assert row.updated_at == LATER


async def _rated_at(engine, item_id):
    """Время оценки прямо из базы: наружу ни одна из двух дат не выходит вовсе,
    и спросить их можно только так."""
    async with engine.connect() as connection:
        return (await connection.execute(
            select(rating_table.c.created_at)
            .where(rating_table.c.item_id == item_id)
        )).one().created_at


async def test_the_review_written_before_the_score_is_not_the_time_of_rating(
    sessions, engine, card
):
    """`created_at` — момент, когда карточка стала оценённой, а не когда завелась
    строка. Рецензия строку заводит, оценённой карточку не делает, и первая
    оценка обязана переставить время на себя.

    Вторая рецензия — обратная сторона того же условия: писать её можно сколько
    угодно, времени оценки это не касается."""
    much_later = LATER + timedelta(days=1)
    item_id = await card()
    repository = RatingsRepository(sessions)
    await repository.set_review(item_id, "пока не смотрел", now=WHEN)
    await repository.set_score(item_id, 8.0, now=LATER)

    assert await _rated_at(engine, item_id) == LATER

    await repository.set_review(item_id, "посмотрел", now=much_later)

    assert await _rated_at(engine, item_id) == LATER


async def test_rating_anew_after_taking_the_score_away_stamps_a_fresh_time(
    sessions, engine, card
):
    """Снятая оценка — снятый факт: следующая ставится с нуля и временем себя.

    Строка при этом никуда не девается — `set_score(None)` её не сносит, — то
    есть отличить «оценка появилась» от «строка появилась» больше нечем, кроме
    самой оценки."""
    much_later = LATER + timedelta(days=1)
    item_id = await card()
    repository = RatingsRepository(sessions)
    await repository.set_score(item_id, 3.0, now=WHEN)
    await repository.set_score(item_id, None, now=LATER)
    await repository.set_score(item_id, 4.0, now=much_later)

    assert await _rated_at(engine, item_id) == much_later


async def test_rating_a_game_anew_after_clearing_the_aspects_stamps_a_fresh_time(
    sessions, engine, card
):
    """У игры оценка снимается снятием всех трёх шкал: среднее из ничего пусто.
    Выставленная после этого шкала заводит оценку заново, а не правит прежнюю.

    Путь сюда свой: `set_aspects` пишет оценку выведенной, а не переданной, и
    условие «прежней оценки не было» обязано смотреть на неё же."""
    much_later = LATER + timedelta(days=1)
    item_id = await card(Kind.GAME)
    repository = RatingsRepository(sessions)
    await repository.set_aspects(item_id, 8, 7, 7, now=WHEN)
    await repository.set_aspects(item_id, None, None, None, now=LATER)
    await repository.set_aspects(item_id, 6, None, None, now=much_later)

    assert await _rated_at(engine, item_id) == much_later


async def test_a_second_write_does_not_add_a_second_row(sessions, engine, card):
    """Оценка у карточки одна: запись поверх — обновление, а не ещё строка."""
    item_id = await card()
    repository = RatingsRepository(sessions)
    await repository.set_score(item_id, 6.0, now=WHEN)
    await repository.set_score(item_id, 9.0, now=LATER)

    async with engine.connect() as connection:
        rows = (await connection.execute(select(rating_table.c.item_id))).all()
    assert len(rows) == 1


async def test_review_survives_a_score_change(sessions, card):
    item_id = await card()
    repository = RatingsRepository(sessions)
    await repository.set_score(item_id, 7.0, now=WHEN)
    await repository.set_review(item_id, "хорошо", now=WHEN)
    await repository.set_score(item_id, 8.0, now=LATER)
    stored = await repository.get(item_id)
    assert stored.review == "хорошо"
    assert stored.score == 8.0


async def test_a_review_does_not_touch_the_aspects(sessions, card):
    """У игры выставлены шкалы; правка отзыва их не стирает."""
    item_id = await card(Kind.GAME)
    repository = RatingsRepository(sessions)
    await repository.set_aspects(item_id, 8, 7, 7, now=WHEN)
    await repository.set_review(item_id, "затянуто", now=LATER)

    stored = await repository.get(item_id)
    assert (stored.visual, stored.narrative, stored.gameplay) == (8, 7, 7)


async def test_a_score_does_not_touch_the_aspects(sessions, card):
    """Каждый метод пишет своё и только своё: запись общей оценки поверх шкал
    их не трогает. Проверяется отдельно от отзыва — это разные записи."""
    item_id = await card(Kind.GAME)
    repository = RatingsRepository(sessions)
    await repository.set_aspects(item_id, 8, 7, 7, now=WHEN)
    await repository.set_score(item_id, 5.0, now=LATER)

    stored = await repository.get(item_id)
    assert (stored.visual, stored.narrative, stored.gameplay) == (8, 7, 7)
    assert stored.score == 5.0


async def test_a_review_does_not_touch_the_score(sessions, card):
    """Обратная половина к «отзыв переживает смену оценки»: и оценка переживает
    смену отзыва."""
    item_id = await card()
    repository = RatingsRepository(sessions)
    await repository.set_score(item_id, 7.0, now=WHEN)
    await repository.set_review(item_id, "хорошо", now=LATER)

    assert (await repository.get(item_id)).score == 7.0


async def test_clear_removes_the_row_and_the_card_stays(sessions, card):
    """Карточка, с которой сняли оценку, остаётся в библиотеке."""
    item_id = await card()
    repository = RatingsRepository(sessions)
    await repository.set_score(item_id, 8.0, now=WHEN)
    await repository.clear(item_id)

    assert await repository.get(item_id) is None
    assert await LibraryRepository(sessions).get(item_id) is not None


async def test_clear_takes_only_the_asked_card(sessions, card):
    """Без сравнения с `item_id` снятие оценки стёрло бы всю таблицу."""
    mine = await card(source_id="1")
    other = await card(source_id="2")
    repository = RatingsRepository(sessions)
    await repository.set_score(mine, 8.0, now=WHEN)
    await repository.set_score(other, 4.0, now=WHEN)

    await repository.clear(mine)

    assert (await repository.get(other)).score == 4.0


async def test_get_takes_the_asked_card_and_not_just_any(sessions, card):
    mine = await card(source_id="1")
    other = await card(source_id="2")
    repository = RatingsRepository(sessions)
    await repository.set_score(mine, 8.0, now=WHEN)
    await repository.set_score(other, 4.0, now=WHEN)

    assert (await repository.get(other)).item_id == other


async def test_no_rating_yet_is_not_an_error(sessions, card):
    item_id = await card()
    assert await RatingsRepository(sessions).get(item_id) is None
