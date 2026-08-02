"""Чужие метки жанров в наши жанры."""

from collections.abc import Iterable

from backend.model import Genre, GenreRule, GenreSource
from backend.storage.repository.genres import GenresRepository
from backend.unique import unique

Book = dict[GenreSource, tuple[GenreRule, ...]]
Marked = Iterable[tuple[GenreSource, str]]


def _fires(rule: GenreRule, marks: frozenset[str], known: frozenset[str]) -> bool:
    if not rule.required <= marks or rule.forbidden & marks:
        return False
    return not (rule.alone and known - rule.required)


def matched(rules: tuple[GenreRule, ...], marks: Iterable[str]) -> list[Genre]:
    """Правила источника, приложенные ко всему набору меток игры сразу.

    Набором, а не по метке: одиночная метка врёт. У Fallout 2 хвостовое
    «Приключение» сделало бы квест, у Stardew Valley «Песочница» — выживание, и
    порог по весу тут не спасает: у Stardew метка тяжёлая.

    Незнакомое молча отбрасывается: имена в справочнике наши, и пополняют его
    руками. Карточка приезжает без этого жанра, и всё."""
    present = frozenset(marks)
    # Известное — всё, что справочник этого источника называет хоть где-то, а не
    # только требуемое: «без любой другой метки из этой таблицы» сказано про
    # таблицу целиком. Сегодня наборы совпадают — запрещённое вложено в
    # требуемое во всех четырёх книгах, — но первое же правило, запретившее
    # метку, которую нигде не требуют, сделало бы её невидимой для `alone`.
    known = present & frozenset(
        ext_id for rule in rules for ext_id in rule.required | rule.forbidden
    )
    return unique(rule.genre for rule in rules if _fires(rule, present, known))


async def book_for(genres: GenresRepository, spaces: Iterable[GenreSource]) -> Book:
    """Правила по пространствам меток, по одному запросу на пространство."""
    book: Book = {}
    for space in spaces:
        if space not in book:
            book[space] = await genres.rules(space)
    return book


def genres_of(book: Book, marked: Marked) -> tuple[Genre, ...]:
    """Метки карточки, разложенные по пространствам и разрешённые каждое своими
    правилами.

    Пространств у карточки сегодня одно, но тип границы допускает несколько, и
    смешать их в один набор нельзя: `19` у Steam и `19` у GOG — разные метки."""
    by_space: dict[GenreSource, set[str]] = {}
    for space, ext_id in marked:
        by_space.setdefault(space, set()).add(ext_id)
    return tuple(unique(
        genre
        for space, marks in by_space.items()
        for genre in matched(book[space], marks)
    ))


async def resolved_genres(genres: GenresRepository, marked: Marked) -> list[int]:
    """Метки карточки в наши `genre.id` — тем, кто их записывает."""
    marked = tuple(marked)
    book = await book_for(genres, (space for space, _ in marked))
    return [genre.id for genre in genres_of(book, marked)]
