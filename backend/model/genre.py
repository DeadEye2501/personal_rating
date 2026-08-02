"""Жанр на границе слоёв и правило, которое к нему ведёт."""

from dataclasses import dataclass

from backend.model.kinds import GenreKind


@dataclass(frozen=True, slots=True)
class Genre:
    id: int
    name: str
    kind: GenreKind


@dataclass(frozen=True, slots=True)
class GenreRule:
    """Когда набор чужих меток означает наш жанр.

    Одна метка означает жанр не всегда: у Fallout 2 хвостовое «Приключение»
    сделало бы квест, а у Stardew Valley тяжёлая «Ролевая игра» — ролевую игру.
    Отсюда условие над всем набором сразу, а не перевод метки поштучно.

    `alone` — правило срабатывает, только если других известных меток этого
    источника у игры нет вовсе. Перечислять их в `forbidden` пришлось бы
    сотнями: у Steam в справочнике 211 различных меток."""

    genre: Genre
    required: frozenset[str]
    forbidden: frozenset[str] = frozenset()
    alone: bool = False
