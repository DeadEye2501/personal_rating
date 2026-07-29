"""Всё, что приложение делает в базе с человеком или студией как с
сущностью: их строки, их роли на карточках и подсказка при вводе имени."""

from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import Column, ColumnElement, Row, Select, Table, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.model import (
    CompanyRole,
    Credit,
    PersonRole,
    Source,
    Suggestion,
    new_source_id,
)
from backend.storage.repository.base import Repository
from backend.storage.session import fold, folded
from backend.storage.tables import (
    company,
    company_credit,
    item,
    person,
    person_credit,
    rating,
    wishlist,
)


class IdentityTaken(Exception):
    """Пара (source, source_id) уже принадлежит другому человеку или студии."""


@dataclass(frozen=True, slots=True)
class Entity:
    """Чем люди отличаются от студий: своими таблицами, своим набором ролей и
    порядком в титрах, которого у студий нет."""

    table: Table
    credit: Table
    roles: Callable[[str], PersonRole | CompanyRole]
    position: Column | None = None


PEOPLE = Entity(person, person_credit, PersonRole, person_credit.c.position)
COMPANIES = Entity(company, company_credit, CompanyRole)


class CreditRepository(Repository):
    """Одна реализация на людей и студии: для приложения они почти
    неразличимы. Расходятся только в порядке в титрах — у студий его нет."""

    def __init__(
        self, sessions: async_sessionmaker[AsyncSession], entity: Entity
    ) -> None:
        super().__init__(sessions)
        self._entity = entity

    @property
    def _link(self) -> Column:
        return self._entity.credit.c[f"{self._entity.table.name}_id"]

    @property
    def _folded_name(self) -> ColumnElement[str]:
        return folded(self._entity.table.c.name)

    def _same_name(self, name: str) -> ColumnElement[bool]:
        return self._folded_name == fold(name.strip())

    def _name_starts_with(self, name: str) -> ColumnElement[bool]:
        # autoescape: подчёркивание и процент в имени — обычные знаки, а не
        # подстановки LIKE.
        return self._folded_name.startswith(fold(name.strip()), autoescape=True)

    async def _found_id(self, statement: Select) -> int | None:
        return await self._maybe(statement, lambda row: row.id)

    async def create(
        self, name: str, source: Source | None = None, source_id: str | None = None
    ) -> int:
        return await self._created(
            self._entity.table.insert()
            .values(name=name, source=source, source_id=source_id)
            .returning(self._entity.table.c.id),
            IdentityTaken(f"{source}:{source_id} уже занят"),
        )

    async def create_manual(self, name: str) -> int:
        """Заведённый руками получает свою идентичность — как и ручная
        карточка. Иначе он попал бы в корзину «идентичности нет вовсе»,
        которая отведена студиям из магазинов."""
        return await self.create(name, Source.MANUAL, new_source_id())

    async def find_by_source(self, source: Source, source_id: str) -> int | None:
        return await self._found_id(
            select(self._entity.table.c.id).where(
                self._entity.table.c.source == source,
                self._entity.table.c.source_id == source_id,
            )
        )

    async def find_by_name(self, name: str) -> list[int]:
        """Все тёзки. Выбирает между ними человек, а не мы."""
        rows = await self._rows(
            select(self._entity.table.c.id)
            .where(self._same_name(name))
            .order_by(self._entity.table.c.id)
        )
        return [row.id for row in rows]

    async def find_anonymous_by_name(self, name: str) -> int | None:
        """Тёзка без идентичности. Прилипать к чужой нельзя ни в какую
        сторону: ни приехавшему к ручному, ни голой строке к приехавшему.

        Безымянных тёзок бывает и двое — `create` публичен, — поэтому берётся
        первый по номеру, а не все найденные."""
        return await self._found_id(
            select(self._entity.table.c.id)
            .where(self._same_name(name), self._entity.table.c.source_id.is_(None))
            .order_by(self._entity.table.c.id)
            .limit(1)
        )

    async def ensure(self, credit: Credit) -> int:
        """Найти существующего или завести нового."""
        if credit.source is not None and credit.source_id is not None:
            found = await self.find_by_source(credit.source, credit.source_id)
            if found is not None:
                return found
            return await self.create(credit.name, credit.source, credit.source_id)

        found = await self.find_anonymous_by_name(credit.name)
        return found if found is not None else await self.create(credit.name)

    async def attach(
        self,
        item_id: int,
        entity_id: int,
        role: PersonRole | CompanyRole,
        position: int | None = None,
    ) -> None:
        values = {"item_id": item_id, self._link.name: entity_id, "role": role}
        if self._entity.position is not None:
            values["position"] = position
        await self._run(
            insert(self._entity.credit).values(**values).on_conflict_do_nothing()
        )

    async def detach_all(self, item_id: int) -> None:
        await self._run(self._clearing(self._entity.credit, item_id))

    async def credits_of(self, item_id: int) -> list[Credit]:
        table, credit = self._entity.table, self._entity.credit
        columns = [table.c.name, table.c.source, table.c.source_id, credit.c.role]
        if self._entity.position is not None:
            columns.append(self._entity.position)

        return await self._mapped(
            select(*columns)
            .join_from(credit, table, self._link == table.c.id)
            .where(credit.c.item_id == item_id)
            .order_by(self._entity.position
                      if self._entity.position is not None else table.c.name),
            self._to_credit,
        )

    async def suggest(self, name: str, limit: int = 10) -> list[Suggestion]:
        """Строки подсказки при вводе имени. Тёзки различаются не
        метаданными, а тем, чем каждый из них известен в твоей библиотеке."""
        rows = await self._rows(
            select(self._entity.table.c.id, self._entity.table.c.name)
            .where(self._name_starts_with(name))
            .order_by(self._entity.table.c.name, self._entity.table.c.id)
            .limit(limit)
        )

        found = []
        for row in rows:
            title, item_id = await self._hint(row.id)
            found.append(Suggestion(row.id, row.name, title, item_id))
        return found

    def _linked(self, entity_id: int) -> Select:
        """Общее у трёх ступеней подсказки. Вынесено не ради краткости:
        потерять здесь отбор по человеку в одной ступени из трёх — значит
        показать в подсказке чужую карточку."""
        return (
            select(item.c.title, item.c.id)
            .join_from(self._entity.credit, item,
                       self._entity.credit.c.item_id == item.c.id)
            .where(self._link == entity_id)
        )

    async def _hint(self, entity_id: int) -> tuple[str, int | None]:
        """Чем он известен в твоей библиотеке: сперва самое высоко оценённое
        тобой, потом самое свежее из отложенного, потом любая связанная
        карточка. Третья ступень не для красоты — человек, снявшийся только в
        неоценённых и неотложенных карточках, обычное дело."""
        linked = self._linked(entity_id)
        steps = (
            linked.join(rating, rating.c.item_id == item.c.id)
            .where(rating.c.score.is_not(None))
            .order_by(rating.c.score.desc())
            .limit(1),
            linked.join(wishlist, wishlist.c.item_id == item.c.id)
            .order_by(wishlist.c.added_at.desc())
            .limit(1),
            linked.limit(1),
        )
        for statement in steps:
            row = await self._row(statement)
            if row is not None:
                return row.title, row.id
        return "", None

    def _to_credit(self, row: Row) -> Credit:
        return Credit(
            name=row.name,
            # Роль возвращается перечислением, а не сырой строкой из базы:
            # `==` у StrEnum истинно и для строки, а `is` и `isinstance` —
            # нет, и два пути чтения разошлись бы молча.
            role=self._entity.roles(row.role),
            position=row.position if self._entity.position is not None else None,
            source=Source(row.source) if row.source else None,
            source_id=row.source_id,
        )


def people(sessions: async_sessionmaker[AsyncSession]) -> CreditRepository:
    return CreditRepository(sessions, PEOPLE)


def companies(sessions: async_sessionmaker[AsyncSession]) -> CreditRepository:
    return CreditRepository(sessions, COMPANIES)
