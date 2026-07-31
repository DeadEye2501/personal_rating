"""Один репозиторий на людей и на студий — различает их только описатель.

Подсказка при вводе имени живёт здесь же, а не отдельным модулем: она делит с
«всё с этим человеком» запрос `_linked`, и вынос потребовал бы третьего модуля
ради одного объявления. Отклонение измеренное, а не незамеченное."""

from sqlalchemy import Column, ColumnElement, Select, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.model import (
    CompanyRole,
    Credit,
    Kind,
    PersonRole,
    Source,
    Suggestion,
    new_source_id,
)
from backend.storage.repository.base import Repository
from backend.storage.entity import COMPANIES, PEOPLE, Entity
from backend.storage.rows import to_credit
from backend.storage.session import fold, folded
from backend.storage.statements import clearing
from backend.storage.tables import (
    item,
    rating,
    wishlist,
)


class IdentityTaken(Exception):
    """Пара (source, source_id) уже принадлежит другому человеку или студии."""


def _outer(row) -> str | None:
    """Идентификатор, по которому строку можно спросить у внешнего источника.

    У заведённого руками он тоже заполнен — свой `uuid4` под источником
    `manual`, — но спросить по нему некого.

    Знание про `manual` лежит в хранилище, а не в сервисе, намеренно: пишет эту
    условность `create_manual` двадцатью строками ниже, и читатель рядом с
    писателем разумнее, чем в другом слое.

    Чей это идентификатор, наружу не отдаётся: людей заводит только TMDB, у
    компаний внешней половины нет вовсе, и второму источнику людей взяться
    неоткуда. Появись он — сравнивать источник с клиентом придётся здесь же."""
    return row.source_id if row.source and row.source != Source.MANUAL else None


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
        return self._entity.link

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
        await self._run(clearing(self._entity.credit, item_id))

    async def credits_of(self, item_id: int) -> list[Credit]:
        table, credit = self._entity.table, self._entity.credit
        # `id` берётся ради клика по имени: искать связанное надо по строке, а
        # не по имени — имя тёзку не различает.
        columns = [table.c.id, table.c.name, table.c.source, table.c.source_id,
                   credit.c.role]
        if self._entity.position is not None:
            columns.append(self._entity.position)

        return await self._mapped(
            select(*columns)
            .join_from(credit, table, self._link == table.c.id)
            .where(credit.c.item_id == item_id)
            .order_by(self._entity.position
                      if self._entity.position is not None else table.c.name),
            lambda row: to_credit(row, self._entity),
        )

    async def identity_of(self, entity_id: int) -> tuple[str, str | None] | None:
        """Имя строки и её идентичность **у внешнего источника**, либо `None`
        вместо пары, если строки нет вовсе. Когда идентичность считается пустой
        — у `_outer`.

        Одним запросом, а не двумя: клику нужно и то и другое сразу — по
        идентичности он спрашивает источник, а без неё спрашивает по имени."""
        return await self._maybe(
            select(self._entity.table.c.name, self._entity.table.c.source,
                   self._entity.table.c.source_id)
            .where(self._entity.table.c.id == entity_id),
            lambda row: (row.name, _outer(row)),
        )

    async def items_of(self, entity_id: int, kind: Kind) -> list[int]:
        """Всё, с чем связан этот человек или студия, в пределах вкладки.

        Вкладка — первичный фильтр: во вкладке фильмов сериалов не бывает нигде,
        и клик по человеку её не отменяет.

        Предела нет: «покажи всё с ним» обрезанным ответом не отвечается, а
        следующей страницы у этого жеста не бывает — обрезанное стало бы
        недостижимым.

        `distinct` обязателен: один человек бывает на карточке и режиссёром, и
        актёром — это две строки связи и одна карточка.

        Порядок — по своей оценке, высокие сверху; неоценённые следом. Спека его
        не называет, но вопрос тот же, что в «Оценённых»: что у этого человека
        стоит смотреть. SQLite при `DESC` кладёт `NULL` вниз сам."""
        rows = await self._rows(
            self._linked(entity_id)
            .with_only_columns(item.c.id)
            .where(item.c.kind == kind)
            .distinct()
            .join(rating, rating.c.item_id == item.c.id, isouter=True)
            .order_by(rating.c.score.desc(), item.c.id)
        )
        return [row.id for row in rows]

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
        """Карточки этой сущности: соединение со связью и отбор по ней.

        Общее у трёх ступеней подсказки и у страницы «всё с этим человеком».
        Вынесено не ради краткости: потерять здесь отбор по человеку в одной
        ступени из четырёх — значит показать чужую карточку."""
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

def people(sessions: async_sessionmaker[AsyncSession]) -> CreditRepository:
    return CreditRepository(sessions, PEOPLE)


def companies(sessions: async_sessionmaker[AsyncSession]) -> CreditRepository:
    return CreditRepository(sessions, COMPANIES)
