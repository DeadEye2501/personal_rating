"""Чем человек отличается от студии в схеме.

Лежит рядом с `statements.py`, а не в `repository/`: это описание схемы, и его
читает `rows.py`, который сам импортируют все репозитории. Внутри `repository/`
получался бы цикл на уровне пакетов."""

from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import Column, Table

from backend.model import CompanyRole, PersonRole
from backend.publishers import alike
from backend.storage.tables import company, company_credit, person, person_credit


@dataclass(frozen=True, slots=True)
class Entity:
    """Чем люди отличаются от студий: своими таблицами, своим набором ролей и
    порядком в титрах, которого у студий нет."""

    table: Table
    credit: Table
    roles: Callable[[str], PersonRole | CompanyRole]
    position: Column | None = None
    # Как узнать одно и то же имя в разных написаниях. У людей никак: имя пишут
    # одним способом, а тёзки — это разные люди, и склеивать их нельзя. У студий
    # иначе: «Издательство АСТ», «АСТ», `Ast` и `ACT` — одно издательство, и
    # различает их не равенство строк, а близость написаний. Замерено
    # 23.08.2026 на слепой разметке 111 написаний живой выдачи.
    #
    # Область шире области замера, и это названо нарочно: идентичности нет ни у
    # одной студии магазинов, значит через правило проходят и разработчики с
    # издателями игр, а мерили его на книжных написаниях. Проверено ревью
    # 23.08.2026 перебором 107 правдоподобных имён обеих половин (5671 пара):
    # ложная склейка была одна, `Vintage Books` против `Vantage Press`, и она
    # закрыта требованием совпасть первой гласной.
    alike: Callable[[str, str], bool] | None = None

    @property
    def link(self) -> Column:
        """Колонка связи зовётся по имени своей таблицы: `person_id`,
        `company_id`."""
        return self.credit.c[f"{self.table.name}_id"]


PEOPLE = Entity(person, person_credit, PersonRole, person_credit.c.position)
COMPANIES = Entity(company, company_credit, CompanyRole, alike=alike)
