"""Карточку удалили, пока по ней шла работа: что делает доехавшая запись.

Своим модулем, потому что предмет один и общий для трёх слоёв: оценка, закладка
и обогащение попадают в это состояние разными путями, а следствие у них одно —
запись, которой больше не к чему привязаться.
"""

import pytest

from backend.model import Denied, ExternalRating, RatingSource
from backend.storage.repository.external import ExternalRatingsRepository
from backend.storage.repository.library import LibraryRepository
from backend.storage.repository.ratings import RatingsRepository
from backend.storage.repository.wishlist import WishlistRepository
from tests.conftest import MOMENT


async def test_a_rating_of_a_gone_card_is_a_denial_and_not_a_database_error(card,
                                                                          sessions):
    """Оценка ставится по уже нарисованной ленте, а карточку успели удалить из
    другого окна.

    Наружу это обязано выйти отказом проекта, а не `IntegrityError` из
    SQLAlchemy: мост переводит незнакомое исключение в «непредвиденное», и
    страница отвечает человеку общей бедой на действие, которое для него прошло
    успешно, а в подробностях уезжает текст SQLite. Правило записано у соседнего
    способа записи — «знание о SQLAlchemy не едет вверх по слоям», — и
    держалось у двух способов из трёх."""
    item_id = await card()
    await LibraryRepository(sessions).delete(item_id)

    with pytest.raises(Denied):
        await RatingsRepository(sessions).set_score(item_id, 8.0, now=MOMENT)


async def test_a_bookmark_of_a_gone_card_is_a_denial_too(card, sessions):
    """Тот же путь, что у оценки, и он короче: закладка ставится одним нажатием
    по строке ленты."""
    item_id = await card()
    await LibraryRepository(sessions).delete(item_id)

    with pytest.raises(Denied):
        await WishlistRepository(sessions).add(item_id, MOMENT)


async def test_an_arriving_external_rating_of_a_gone_card_is_a_denial(card,
                                                                     sessions):
    """Круг агрегаторов живёт до двадцати секунд на источник, и карточку успевают
    удалить, пока он едет."""
    item_id = await card()
    await LibraryRepository(sessions).delete(item_id)

    with pytest.raises(Denied):
        await ExternalRatingsRepository(sessions).record(
            item_id, ExternalRating(RatingSource.IMDB, 7.5, MOMENT))
