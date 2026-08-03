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
    # Пара «чьё пространство и метка в нём»: справочник у каждого источника свой,
    # и `19` у Steam — это Action, а у GOG такой метки нет вовсе. Плоский список
    # пространства не несёт, и правила пришлось бы искать наугад.
    genre_ext_ids: tuple[tuple[GenreSource, str], ...] = field(default_factory=tuple)
    source_rating: float | None = None
    # Другие написания этой же строки, по которым её узнаёт склейка выдачи.
    # Сегодня это слаг GOG: у него показываемое название локализовано — «Ведьмак
    # 3: Дикая Охота» против «The Witcher 3: Wild Hunt» у Steam, — и совпасть
    # они не могут никогда, а слаг совпадает.
    #
    # Отдельным полем, а не в `original_title`: то едет на экран, а слаг человеку
    # показывать нечего. У old-games там лежит второе название игры, и склейка
    # берёт оба поля.
    aliases: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class PersonHit:
    """Человек, найденный у источника по имени.

    Своего типа он требует потому, что `SearchHit` — это карточка, а тут не
    карточка: ни года, ни постера, ни жанров. Через мост он не ходит — сервис
    берёт из него идентификатор, а наружу едут уже `CardView`.

    Имени в нём нет намеренно: отбора среди найденных не бывает — что источник
    вернул на имя, то и ответ, — и читать имя было бы некому."""

    source_id: str
