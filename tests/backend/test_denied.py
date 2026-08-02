"""Отказ операции — нормальный ход событий, и клиент обязан их различать."""

import pytest

from backend.model import (
    Dangling,
    BadImage,
    Denied,
    IdentityTaken,
    ItemExists,
    Kind,
    TagExists,
    WrongTagKind,
)
from backend.service.images import crop_to_cover
from backend.storage.posters import NotOpened
from backend.storage.repository.external import ExternalIdTaken
from backend.storage.repository.tags import TagsRepository

SIX = [ItemExists, TagExists, WrongTagKind, IdentityTaken, BadImage, Dangling]


async def test_a_repository_raises_the_ancestor(sessions):
    """Следствие, а не объявление: отказ, поднятый настоящей записью в базу,
    ловится общим предком."""
    tags = TagsRepository(sessions)
    await tags.create(Kind.MOVIE, "драма")

    with pytest.raises(Denied):
        await tags.create(Kind.MOVIE, "драма")


async def test_two_denials_of_different_operations_keep_different_types(sessions):
    """Предок ловит оба, но слипнуться им нельзя: род отказа выбирается по типу,
    и одним типом на двоих человеку показали бы «имя занято» вместо «это не
    картинка». Оба отказа здесь поднимает боевой код, а не сам тест."""
    tags = TagsRepository(sessions)
    await tags.create(Kind.MOVIE, "драма")

    with pytest.raises(Denied) as taken:
        await tags.create(Kind.MOVIE, "драма")
    with pytest.raises(Denied) as broken:
        crop_to_cover(b"not a picture")

    assert type(taken.value) is not type(broken.value)


def test_the_denials_of_the_model_are_six_and_all_of_them_are_here():
    """Список набран руками, и сверяется он с настоящим потомством предка: отказ,
    заведённый шестым, иначе не попал бы ни в одну проверку — а ради того, чтобы
    мост ловил один тип вместо перечисления, предок и заведён.

    Считаются только объявленные в модели. Наследоваться от `Denied` вправе и
    мост — так `bridge/world.py` объявляет «вставленное не похоже на адрес»,
    и это не отказ бэкенда, а отказ стыка, доезжающий до плашки тем же путём.
    Без этого отбора проверка ещё и зависела бы от того, какие модули успел
    загрузить прогон.

    Отказ **вне** иерархии — свой `Exception` в хранилище — этим не ловится:
    такой не увидит и мост, и заметить его может только чтение."""
    ours = {kind for kind in Denied.__subclasses__()
            if kind.__module__.startswith("backend.model")}

    assert ours == set(SIX)
    assert len(set(SIX)) == 6


def test_a_closed_poster_store_is_not_a_denial():
    """Хранилище не открыли — это поломка сборки, а не занятое имя тега: она
    обязана долететь до лога, а не стать вежливым отказом на странице."""
    assert not issubclass(NotOpened, Denied)


def test_a_taken_external_id_is_not_a_denial_either():
    """Он не пересекает границу вовсе: его ловит и пишет в лог сам `Enricher`, а
    у привязки на этом месте поднимается `ItemExists`. Класс в модели без
    сегодняшнего потребителя — это «на всякий случай»."""
    assert not issubclass(ExternalIdTaken, Denied)
