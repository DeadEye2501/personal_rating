"""Форма правила справочника: как оно записано в объявлениях."""

from typing import NamedTuple


class Rule(NamedTuple):
    """Когда набор чужих меток означает наш жанр.

    Метки пишутся строкой через запятую, а не списками: справочник правят
    глазами, и три пары скобок на каждой из трёх с половиной сотен строк
    читались бы вдвое хуже.

    `alone` — «и никакой другой известной метки этого источника рядом».
    Перечислить их в `without` нельзя: у Steam их две с лишним сотни."""

    genre: str
    marks: str
    without: str = ""
    alone: bool = False

    def required(self) -> list[str]:
        return _split(self.marks)

    def forbidden(self) -> list[str]:
        return _split(self.without)


def _split(written: str) -> list[str]:
    return [one.strip() for one in written.split(",") if one.strip()]
