"""Список убранного: шесть слов в строке поиска показывают его вместо выдачи.

Решение пользователя 03.08.2026 — `docs/specs/2026-08-03-removed-list.md`.
Возвращается не карточка, а память о ней: игра снова находится поиском, но
оценки, тегов и обложки у неё нет — их удалили вместе с карточкой.
"""

import pytest

from backend.model import Found, Kind, Source
from tests.conftest import FakeSearch, a_game, an_item, hit
from tests.wiring import search_service

WORDS = ["удалено", "удалённое", "удаленный", "УДАЛЁННЫЕ", "deleted",
         "  removed  "]


@pytest.mark.parametrize("word", WORDS)
async def test_a_word_of_the_command_shows_what_was_removed(
        sessions, reference, removed, word):
    """Слов шесть, регистр не различается, `е` и `ё` считаются одной буквой.

    Пробелы по краям снимаются: строка приходит из поля ввода, и лишний пробел
    в конце — обычное дело, а «почему-то не сработало» человек объяснить не
    сможет."""
    await removed.remember(a_game())
    steam = FakeSearch(Found([]), name="steam")

    answer = await search_service(sessions, steam).external(Kind.GAME, word)

    assert [one.title for one in answer.views] == ["Fallout 2"]
    assert answer.removed is True


async def test_the_command_does_not_go_to_the_sources(sessions, reference,
                                                      removed):
    """Сеть не трогается вовсе: спрашивать магазины про слово «удалённые»
    незачем, а ждать их отказа человек будет секундами."""
    steam = FakeSearch(Found([]), name="steam")

    await search_service(sessions, steam).external(Kind.GAME, "удалённые")

    assert steam.asked == []


async def test_a_game_named_deleted_is_still_searched(sessions, reference,
                                                      removed):
    """Сравнивается вся строка целиком, а не вхождение слова. Иначе игра, у
    которой в названии стоит `deleted`, перестала бы искаться вовсе — тихо, без
    следа."""
    steam = FakeSearch(Found([
        hit("1", "Deleted Sector", source=Source.STEAM, kind=Kind.GAME),
    ]), name="steam")

    answer = await search_service(sessions, steam).external(
        Kind.GAME, "deleted sector")

    assert [one.title for one in answer.views] == ["Deleted Sector"]
    assert answer.removed is False


async def test_the_list_is_narrowed_by_the_tab(sessions, reference, removed):
    """Вкладка — первичный фильтр везде. Свидетель с обоими типами: со списком
    из одних игр «сузили вкладкой» неотличимо от «отдали всё»."""
    await removed.remember(a_game())
    await removed.remember(
        an_item("550", "Бойцовский клуб", kind=Kind.MOVIE, source=Source.TMDB))

    answer = await search_service(sessions).external(Kind.MOVIE, "удалённые")

    assert [one.title for one in answer.views] == ["Бойцовский клуб"]


async def test_the_command_leaves_the_own_half_empty(sessions, reference,
                                                     removed, card):
    """Своя половина поиска молчит: показать список дважды — разными строками и
    в разном виде — хуже, чем показать один раз.

    Первым приходит именно она, поэтому молчать обязана она, а не список.

    **Свидетель нашёлся бы, не будь ветки:** в базе лежит карточка «Удалённые
    сцены», и без перехвата её вернул бы обычный поиск по своей библиотеке. С
    пустой библиотекой проверка была бы зелёной при любой поломке."""
    await card(Kind.GAME, "1", "Удалённые сцены")
    assert await search_service(sessions).local(Kind.GAME, "удалённые сцены")

    assert await search_service(sessions).local(Kind.GAME, "удалённые") == []


async def test_an_ordinary_query_is_not_the_command(sessions, reference,
                                                    removed):
    """Признак поднимается только командой. Без этой половины «признак есть»
    неотличимо от «признак всегда истина», и обычная выдача рисовалась бы
    строками с кнопкой `restore`."""
    steam = FakeSearch(Found([
        hit("1", "Fallout", source=Source.STEAM, kind=Kind.GAME),
    ]), name="steam")

    answer = await search_service(sessions, steam).external(Kind.GAME, "fallout")

    assert answer.removed is False


async def test_forgetting_does_not_reach_across_the_kind(removed):
    """Снятие идёт по тройке, и тип содержимого в неё входит: у TMDB фильмы и
    сериалы нумеруются порознь и сталкиваются числами — `tmdb/1399` это и фильм,
    и «Игра престолов».

    Обратная операция закрыта тем же свидетелем, что и `known`: без него
    возврат фильма молча вернул бы одноимённый по номеру сериал."""
    await removed.remember(
        an_item("1399", "Фильм", kind=Kind.MOVIE, source=Source.TMDB))
    await removed.remember(
        an_item("1399", "Игра престолов", kind=Kind.SERIES, source=Source.TMDB))

    await removed.forget(Kind.MOVIE, Source.TMDB, "1399")

    assert [one.title for one in await removed.listing(Kind.SERIES)] == [
        "Игра престолов"]


async def test_a_title_that_only_looks_like_the_command_is_searched(
        sessions, reference, removed):
    """Слов ровно шесть, и приведение не вправе делать их больше.

    Свидетель настоящий: «The Deleted» — сериал 2016 года. Общее приведение
    названий выбрасывает артикли где угодно, и через него `the deleted`
    становилось командой — то есть сериал не находился бы никогда и молча.
    Ровно тот ущерб, ради которого спека требует сравнивать строку целиком."""
    steam = FakeSearch(Found([
        hit("1", "The Deleted", source=Source.STEAM, kind=Kind.GAME),
    ]), name="steam")

    answer = await search_service(sessions, steam).external(
        Kind.GAME, "the deleted")

    assert answer.removed is False
    assert [one.title for one in answer.views] == ["The Deleted"]
