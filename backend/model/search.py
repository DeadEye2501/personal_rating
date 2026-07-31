"""Кандидат в выдаче поиска — то, чем карточка ещё не стала."""

from dataclasses import dataclass, field

from backend.model.kinds import GenreSource, Kind, Source


@dataclass(frozen=True, slots=True)
class SearchHit:
    """В базу не попадает никогда: строка появляется либо из детального
    ответа, либо из формы ручной карточки."""

    kind: Kind
    source: Source
    source_id: str
    title: str

    original_title: str = ""
    year: int | None = None
    synopsis: str = ""
    poster_url: str = ""
    # Пара «чьё пространство и идентификатор в нём»: у магазинов жанр и тег
    # нумеруются порознь, и `9` у Steam — это жанр «Гонки» и тег «Стратегия»
    # одновременно. Плоский список их не различит, а `GenresRepository.resolve`
    # принимает `GenreSource` именно поэтому.
    genre_ext_ids: tuple[tuple[GenreSource, str], ...] = field(default_factory=tuple)
    source_rating: float | None = None


@dataclass(frozen=True, slots=True)
class PersonHit:
    """Человек, найденный у источника по имени.

    Своего типа он требует потому, что `SearchHit` — это карточка, а тут не
    карточка: ни года, ни постера, ни жанров. Через мост он не ходит — сервис
    берёт из него идентификатор, а наружу едут уже `CardView`.

    Имени в нём нет намеренно: отбора среди найденных не бывает — что источник
    вернул на имя, то и ответ, — и читать имя было бы некому."""

    source_id: str
