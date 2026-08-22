"""Типы границы слоёв: их поля, значения и неизменность."""

from dataclasses import MISSING, FrozenInstanceError, is_dataclass

import pkgutil
from importlib import import_module

import pytest

from backend import model
from backend.model import (
    CompanyRole,
    Denied,
    GenreKind,
    GenreSource,
    IdSource,
    Item,
    Kind,
    PersonRole,
    Rating,
    RatingSource,
    Source,
    average_score,
)
from tests.conftest import MOMENT


def test_average_of_three_aspects_is_not_rounded():
    # Спека называет 7.33 как законное значение: округление живёт в показе.
    assert average_score(8, 7, 7) == pytest.approx(7.3333, abs=1e-4)


def test_empty_aspects_do_not_drag_the_average_down():
    assert average_score(8, None, 6) == 7.0


def test_single_aspect_is_its_own_average():
    assert average_score(None, 9, None) == 9.0


def test_no_aspects_at_all_gives_nothing():
    assert average_score(None, None, None) is None


def test_zero_counts_as_a_filled_aspect():
    # Шкала в спеке 1–10, нуля на ней нет — проверяется именно то, что функция
    # отличает выставленное от невыставленного по `is None`, а не по ложности.
    assert average_score(0, 10, None) == 5.0


def boundary_dataclasses():
    """Все датаклассы модели. Собираются обходом её подмодулей, а не списком:
    перечисленный руками отстаёт молча — так и вышло, шесть имён против
    двадцати трёх объявлений.

    Обход идёт по файлам, а не по `model.__all__`, и это не одно и то же:
    забытый в поверхности тип из `__all__` выпал бы вместе с проверкой, а
    клиенту он всё равно открыт — граница слоёв пускает любой `backend.model.*`
    по префиксу, а не по списку."""
    for info in pkgutil.iter_modules(model.__path__):
        submodule = import_module(f"{model.__name__}.{info.name}")
        for declared in vars(submodule).values():
            if (isinstance(declared, type) and is_dataclass(declared)
                    and declared.__module__ == submodule.__name__):
                yield declared


def boundary_denials():
    """Отказы операции — тоже типы границы, но не датаклассы: клиент ловит их по
    имени, и забытое в `__all__` имя ловить нечем. Заморозки от них не требуется,
    поэтому набор отдельный, а не расширенный фильтр у соседа.

    Считаются только объявленные в модели. Наследоваться от `Denied` вправе и
    мост — так `bridge/world.py` объявляет «вставленное не похоже на адрес», — и
    без отбора набор зависел бы от того, какие модули успел загрузить прогон:
    `pytest tests/bridge tests/backend` краснел, а тот же прогон в обратном
    порядке зеленел. Тот же отбор стоит у соседней проверки в `test_denied.py`,
    и по той же причине."""
    yield Denied
    yield from (kind for kind in Denied.__subclasses__()
                if kind.__module__.startswith("backend.model"))


@pytest.mark.parametrize("declared",
                         list(boundary_dataclasses()) + list(boundary_denials()),
                         ids=lambda cls: cls.__name__)
def test_every_boundary_type_is_named_on_the_surface(declared):
    """Поверхность `backend.model` — то, что клиент берёт по имени. Тип, забытый
    в `__all__`, импортируется всё равно, но перестаёт быть объявленным: его не
    видит ни `from backend.model import *`, ни тот, кто читает поверхность,
    чтобы понять, что вообще ездит через границу слоёв."""
    assert declared.__name__ in model.__all__


@pytest.mark.parametrize("declared", list(boundary_dataclasses()),
                         ids=lambda cls: cls.__name__)
def test_boundary_types_are_frozen(declared):
    """Через границу слоёв они ходят между потоками: разморозь один — и
    состояние карточки поедет вслед за ссылкой.

    Присваивание проверяется на пустом объекте, минуя конструктор: у каждого
    типа границы свои обязательные поля, и собирать их значило бы завести тот
    самый список, который уже однажды отстал. Заморозку это наблюдает так же —
    её держит `__setattr__`, а не `__init__`."""
    # Обязательные поля заполняются пустотой: значения здесь ни при чём,
    # проверяется присваивание после сборки. Мимо конструктора идти нельзя —
    # у типов со `slots=True` собранный руками объект ломает сам `__setattr__`.
    required = {
        name: None for name, field in declared.__dataclass_fields__.items()
        if field.default is MISSING and field.default_factory is MISSING
    }
    built = declared(**required)

    # У `Missing` полей нет вовсе, и присваивать приходится чужое имя. Тогда
    # сгенерированный `__setattr__` уходит в ветку `super()`, а у типов со
    # `slots=True` она спотыкается о собственное замыкание CPython и даёт
    # `TypeError` вместо `FrozenInstanceError`. Присваивание не проходит и там,
    # и там — а неизменность и есть предмет проверки.
    field = next(iter(declared.__dataclass_fields__), "чужое_имя")
    refuses = (FrozenInstanceError if declared.__dataclass_fields__
               else (FrozenInstanceError, TypeError))

    with pytest.raises(refuses):
        setattr(built, field, None)


def test_optional_fields_have_sane_defaults():
    # Умолчания уезжают в базу как есть: строка вместо None у необязательного
    # поля — это пустое название вместо «неизвестно».
    item = Item(
        id=1,
        kind=Kind.GAME,
        source=Source.STEAM,
        source_id="292030",
        title="The Witcher 3",
        synced_at=MOMENT,
    )
    assert (item.original_title, item.synopsis, item.poster_url) == ("", "", "")
    assert (item.year, item.released_at, item.runtime) == (None, None, None)
    assert (item.seasons_count, item.episodes_count) == (None, None)


def test_rating_of_a_film_carries_no_aspects():
    rating = Rating(item_id=1, score=8.0)
    assert (rating.visual, rating.narrative, rating.gameplay) == (None, None, None)


# Значения ложатся в базу текстом — они часть схемы, а не деталь кода:
# переименование здесь ломает уже записанные строки, а не только код.
SCHEMA = [
    (Kind, {"movie", "series", "game", "book", "music"}),
    (Source, {"manual", "tmdb", "steam", "gog", "old_games"}),
    (IdSource, {"imdb", "kinopoisk", "steam", "gog"}),
    (RatingSource, {"imdb", "kinopoisk", "tmdb", "rotten", "metacritic",
                    "steam", "gog"}),
    (PersonRole, {"director", "actor", "showrunner", "author",
                  "performer"}),
    (CompanyRole, {"developer", "publisher"}),
    (GenreKind, {"film", "game", "book", "music"}),
    (GenreSource, {"tmdb", "steam", "gog", "old_games"}),
]


@pytest.mark.parametrize(("enum", "expected"), SCHEMA,
                         ids=lambda item: getattr(item, "__name__", ""))
def test_enum_values_match_the_schema(enum, expected):
    """Набор значений, а не привязка члена к значению: обмен двух членов местами
    здесь не виден, и ловят его те тесты, что читают сырую колонку, —
    `test_library.py` для `Kind` и `Source`, `test_credits.py` для ролей,
    `test_tmdb_card.py` для `IdSource`, `test_external_ratings.py` для
    `RatingSource`, фикстура справочника для `GenreSource`.

    Ловят не всех: у `BOOK`, `MUSIC`, `AUTHOR` и `PERFORMER` такого сторожа нет
    — сырую колонку с ними читать негде, пока карточку этих типов заводят
    только руками. Обмен их значений местами сегодня не поймает никто, и это
    известно, а не упущено."""
    assert {member.value for member in enum} == expected
