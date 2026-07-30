"""Чужие метки жанров в наши идентификаторы."""

from backend.model import GenreSource
from backend.storage.repository.genres import GenresRepository
from backend.unique import unique


async def resolved_genres(
    genres: GenresRepository,
    marked: tuple[tuple[GenreSource, str], ...],
) -> list[int]:
    """Пары «пространство и идентификатор» в наши `genre.id`.

    Пространств у одной карточки бывает два — жанры магазина и его теги, — и
    нумеруются они порознь: `9` у Steam это жанр «Гонки» и тег «Стратегия».
    Поэтому справочник спрашивается по каждому пространству отдельно. Дубли
    снимаются: два разных тега нередко ведут в один наш жанр, и `Action RPG`
    вместе с `Ролевая игра` дадут `RPG` дважды.

    Дальше происхождение не помнит никто: наружу едут только наши жанры."""
    spaces: dict[GenreSource, list[str]] = {}
    for space, ext_id in marked:
        spaces.setdefault(space, []).append(ext_id)

    found: list[int] = []
    for space, ext_ids in spaces.items():
        found.extend(await genres.resolve(space, ext_ids))
    return unique(found)
