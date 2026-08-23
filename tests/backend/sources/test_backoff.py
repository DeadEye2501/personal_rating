"""Закрытие источника на срок: общее для тех, кто отказывает по квоте.

Своего модуля у этих проверок раньше не было — они лежали у OMDB, первого
владельца `until_midnight`. С переездом функции в общее это стало ловушкой:
снеси набор одного из двух потребителей, и общий код останется без прямого
сторожа при зелёном наборе."""

from datetime import datetime, timedelta

from backend.sources.backoff import until_midnight


def test_until_midnight_counts_to_the_next_day():
    assert until_midnight(datetime(2026, 7, 27, 23, 0)) == timedelta(hours=1)
    assert until_midnight(datetime(2026, 7, 27, 0, 30)) == timedelta(
        hours=23, minutes=30
    )
