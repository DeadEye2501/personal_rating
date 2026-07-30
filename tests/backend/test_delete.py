"""Удаление карточки из двух файлов базы и что пропадает вместе с ней."""

import pytest

from backend.model import Kind
from backend.service.posters import PosterService
from backend.service.removal import remove_card
from backend.storage.repository.library import LibraryRepository
from backend.storage.repository.ratings import RatingsRepository
from backend.storage.repository.tags import TagsRepository
from backend.storage.repository.wishlist import WishlistRepository
from tests.conftest import PICTURE
from tests.conftest import MOMENT as WHEN


@pytest.fixture
async def service(posters):
    """Сервис обложек поверх тестового хранилища: удаление карточки идёт через
    него, потому что второй файл базы наружу не показывается.

    Клиентов нет вовсе: удаление зовёт один `delete`. Собранный помощник поднял
    бы три живых `AsyncClient` на каждый тест, и никто бы их не закрыл — а тесты
здесь как раз про то, что за обложками отсюда не ходят."""
    return PosterService({}, posters)


async def furnished(sessions, posters, item_id: int, tag: str = "пересмотреть") -> int:
    """Навешивает на карточку всё, что должно уйти вместе с ней. Имя тега —
    параметр: набор один на тип содержимого, и двум карточкам нужен свой."""
    await RatingsRepository(sessions).set_score(item_id, 9.0, now=WHEN)
    tags = TagsRepository(sessions)
    await tags.assign(item_id, await tags.create(Kind.MOVIE, tag))
    await WishlistRepository(sessions).add(item_id, now=WHEN)
    await posters.put(item_id, PICTURE, now=WHEN)
    return item_id


async def test_deletion_summary_lists_what_will_be_lost(sessions, posters, card):
    item_id = await furnished(sessions, posters, await card())
    summary = await LibraryRepository(sessions).deletion_summary(item_id)
    assert summary == {"has_rating": True, "tags": 1, "in_wishlist": True}


async def test_summary_counts_only_the_asked_card(sessions, posters, card):
    """Сводка про эту карточку, а не про библиотеку: соседняя с оценкой,
    тегами и закладкой на неё не влияет."""
    await furnished(sessions, posters, await card(source_id="1"))
    bare = await card(source_id="2")

    summary = await LibraryRepository(sessions).deletion_summary(bare)
    assert summary == {"has_rating": False, "tags": 0, "in_wishlist": False}


ALONE = [
    ("has_rating", {"has_rating": True, "tags": 0, "in_wishlist": False}),
    ("tags", {"has_rating": False, "tags": 1, "in_wishlist": False}),
    ("in_wishlist", {"has_rating": False, "tags": 0, "in_wishlist": True}),
]


@pytest.mark.parametrize(("what", "expected"), ALONE)
async def test_summary_tells_the_three_apart(sessions, card, what, expected):
    """Каждое из трёх — своё, и на карточке, где есть только оно. Вешая всё
    сразу, тест не отличит перепутанные местами поля: сводка «всё есть» сойдётся
    при любой путанице, а «ничего нет» — при любой другой."""
    item_id = await card()
    if what == "has_rating":
        await RatingsRepository(sessions).set_score(item_id, 9.0, now=WHEN)
    elif what == "tags":
        tags = TagsRepository(sessions)
        await tags.assign(item_id, await tags.create(Kind.MOVIE, "один"))
    else:
        await WishlistRepository(sessions).add(item_id, now=WHEN)

    assert await LibraryRepository(sessions).deletion_summary(item_id) == expected


async def test_summary_counts_every_tag(sessions, card):
    """Тегов у карточки бывает несколько, и в сводке их число, а не «есть»."""
    item_id = await card()
    tags = TagsRepository(sessions)
    for name in ("первый", "второй", "третий"):
        await tags.assign(item_id, await tags.create(Kind.MOVIE, name))

    summary = await LibraryRepository(sessions).deletion_summary(item_id)
    assert summary["tags"] == 3


async def test_delete_takes_everything_with_it(sessions, posters, service, card):
    item_id = await furnished(sessions, posters, await card())

    await remove_card(LibraryRepository(sessions), service, item_id)

    assert await LibraryRepository(sessions).get(item_id) is None
    assert await RatingsRepository(sessions).get(item_id) is None
    assert await TagsRepository(sessions).tags_of(item_id) == []
    assert await WishlistRepository(sessions).contains(item_id) is False

    # Постер лежит в другом файле — каскадом он не удалится, только кодом.
    assert await posters.has(item_id) is False


async def test_the_tag_itself_survives_the_card(sessions, posters, service, card):
    """Уходит назначение тега, а не тег: он принадлежит набору, а не карточке."""
    item_id = await furnished(sessions, posters, await card())

    await remove_card(LibraryRepository(sessions), service, item_id)

    names = [
        tag.name for tag in await TagsRepository(sessions).list_for_kind(Kind.MOVIE)
    ]
    assert names == ["пересмотреть"]


async def test_other_cards_are_untouched(sessions, posters, service, card):
    """Удаляется вторая, а не первая: снеси код постер по зашитому номеру —
    на паре, где удаляемая заведена первой, это прошло бы молча."""
    first = await furnished(sessions, posters, await card(source_id="1"))
    second = await furnished(sessions, posters, await card(source_id="2"), "чужой")

    await remove_card(LibraryRepository(sessions), service, second)

    assert await LibraryRepository(sessions).get(first) is not None
    assert await posters.has(first) is True
    assert await RatingsRepository(sessions).get(first) is not None
    assert await WishlistRepository(sessions).contains(first) is True
    assert await posters.has(second) is False


async def test_deleting_a_card_that_is_not_there_is_quiet(sessions, service):
    await remove_card(LibraryRepository(sessions), service, 404)


async def test_a_broken_deletion_leaves_the_card_not_the_poster(sessions, posters,
                                                                service, card,
                                                                monkeypatch):
    """Оборваться удаление может только между двумя файлами базы: общей транзакции
    на них не бывает. Из двух половин уцелеть должна карточка, а не постер.

    Осиротевший постер хуже: `item` заведён без `AUTOINCREMENT`, номер SQLite
    выдаёт повторно, и следующая карточка получила бы чужую обложку молча.
    Карточка без обложки лечится сама — её скачают заново по `poster_url`."""
    item_id = await furnished(sessions, posters, await card())
    library = LibraryRepository(sessions)

    async def refuse(*_args, **_kwargs):
        raise OSError("второй файл базы занят")

    monkeypatch.setattr(library, "_run", refuse)

    with pytest.raises(OSError):
        await remove_card(library, service, item_id)

    assert await posters.has(item_id) is False, \
        "постер остался и достанется карточке с этим же номером"
    assert await LibraryRepository(sessions).get(item_id) is not None
