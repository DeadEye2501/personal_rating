"""Чем человек отличается от студии в схеме.

Лежит рядом с `statements.py`, а не в `repository/`: это описание схемы, и его
читает `rows.py`, который сам импортируют все репозитории. Внутри `repository/`
получался бы цикл на уровне пакетов."""

from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import Column, Table

from backend.model import CompanyRole, PersonRole
from backend.storage.tables import company, company_credit, person, person_credit


@dataclass(frozen=True, slots=True)
class Entity:
    """Чем люди отличаются от студий: своими таблицами, своим набором ролей и
    порядком в титрах, которого у студий нет."""

    table: Table
    credit: Table
    roles: Callable[[str], PersonRole | CompanyRole]
    position: Column | None = None

    @property
    def link(self) -> Column:
        """Колонка связи зовётся по имени своей таблицы: `person_id`,
        `company_id`."""
        return self.credit.c[f"{self.table.name}_id"]


PEOPLE = Entity(person, person_credit, PersonRole, person_credit.c.position)
COMPANIES = Entity(company, company_credit, CompanyRole)
