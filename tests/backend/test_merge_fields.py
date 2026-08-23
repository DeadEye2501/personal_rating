"""Правила слияния полей при привязке: что остаётся своим, что доливается.

Отдельным модулем от самой привязки: здесь чистые функции без базы и без
обложек, там — `Linker` со всеми семью репозиториями. Разошлись они по этому же
шву, когда файл перевалил предел в пятьсот строк."""

from datetime import date

from backend.model import (
    Item,
    Kind,
    Source,
)
from backend.service.linking import merge_fields, overwrite_fields
from tests.conftest import MOMENT, an_item, film_card


def mine(**fields) -> Item:
    """Ручная карточка как объект: слияние проверяется без базы."""
    return Item(id=1, kind=Kind.MOVIE, source=Source.MANUAL, source_id="u",
                title="Интерстеллар", synced_at=MOMENT, **fields)


def test_merge_keeps_what_the_human_typed():
    merged = merge_fields(mine(synopsis="Мой текст"), film_card().item)

    assert merged.title == "Интерстеллар"
    assert merged.synopsis == "Мой текст"


def test_merge_fills_only_the_empty():
    merged = merge_fields(mine(), film_card().item)

    assert merged.year == 2014
    assert merged.runtime == 169


FULL = an_item(
    "83867", "Andor", kind=Kind.SERIES, original_title="Andor",
    year=2022, released_at=date(2022, 9, 21), synopsis="Официальный синопсис",
    poster_url="https://example.com/andor.jpg", runtime=48,
    seasons_count=2, episodes_count=24,
)


def test_every_field_a_source_may_fill_is_filled():
    """Все девять полей поимённо: проверка на трёх из них молчит, когда из набора
    выпадает четвёртое — а выпасть может любое, набор задан списком."""
    merged = merge_fields(mine(), FULL)

    assert (merged.title, merged.original_title) == ("Интерстеллар", "Andor")
    assert (merged.year, merged.released_at) == (2022, date(2022, 9, 21))
    assert merged.synopsis == "Официальный синопсис"
    assert merged.poster_url == "https://example.com/andor.jpg"
    assert merged.runtime == 48
    assert (merged.seasons_count, merged.episodes_count) == (2, 24)


def test_merge_never_moves_identity_or_the_sync_mark():
    merged = merge_fields(mine(), film_card().item)

    assert (merged.id, merged.source, merged.source_id) == (1, Source.MANUAL, "u")
    assert merged.synced_at == MOMENT


def test_overwrite_takes_the_incoming_over_the_own():
    merged = overwrite_fields(mine(synopsis="Набросок"), film_card().item)

    assert merged.title == "Interstellar"
    assert merged.synopsis == "Официальный синопсис"


def test_overwrite_does_not_touch_the_kind_of_the_card():
    """Тип содержимого источник не перезаписывает даже под галочкой: что делать
    со ссылкой на сериал у карточки фильма — не решено, и менять его молча
    нельзя. Попади `kind` в список доливаемых полей — галочка превратила бы
    фильм в сериал.

    Слияние без галочки той же проверки не требует: оно доливает только пустое,
    а непустой `kind` не пуст никогда — упасть такое утверждение не может."""
    series = film_card(item=an_item("1396", "Во все тяжкие", kind=Kind.SERIES)).item

    assert overwrite_fields(mine(), series).kind is Kind.MOVIE


def test_overwrite_keeps_what_the_source_never_sent():
    """Разборщики кладут в непришедшее пустую строку, а не оставляют поле
    незаполненным: у TMDB на русском пустой синопсис — обычное дело, и написанный
    руками текст исчез бы безвозвратно."""
    empty = film_card(item=an_item("157336", "Interstellar")).item

    merged = overwrite_fields(mine(synopsis="Мой текст", runtime=100), empty)

    assert merged.synopsis == "Мой текст"
    assert merged.runtime == 100
