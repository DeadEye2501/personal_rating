"""Мои теги в базе."""

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.sqlite import insert

from backend.model import Kind, Tag, TagExists, WrongTagKind
from backend.naming import capitalized
from backend.storage.repository.base import Repository
from backend.storage.rows import to_tag
from backend.storage.tables import item as item_table
from backend.storage.tables import item_tag as item_tag_table
from backend.storage.tables import tag as tag_table


class TagsRepository(Repository):
    async def create(self, kind: Kind, name: str) -> int:
        """Новый тег встаёт в конец своего набора.

        Конец считается подзапросом внутри вставки, а не отдельным чтением:
        между чтением и записью набор мог бы пополниться, и два тега встали бы
        на одну позицию."""
        tail = (
            select(func.coalesce(func.max(tag_table.c.position), -1) + 1)
            .where(tag_table.c.kind == kind)
            .scalar_subquery()
        )
        return await self._created(
            tag_table.insert()
            .values(name=capitalized(name), kind=kind, position=tail)
            .returning(tag_table.c.id),
            TagExists(f"{kind}:{name} уже заведён"),
        )

    async def list_for_kind(self, kind: Kind) -> list[Tag]:
        return await self._mapped(
            select(tag_table.c.id, tag_table.c.name)
            .where(tag_table.c.kind == kind)
            .order_by(tag_table.c.position),
            to_tag,
        )

    async def reorder(self, kind: Kind, tag_ids: list[int]) -> None:
        """Порядок ручной: строки переставляют перетаскиванием, и пережить
        перезапуск он обязан. Набор в условии — чтобы перестановка в одном не
        перенумеровала соседний."""
        await self._run(*[
            update(tag_table)
            .where(tag_table.c.id == tag_id, tag_table.c.kind == kind)
            .values(position=position)
            for position, tag_id in enumerate(tag_ids)
        ])

    async def rename(self, tag_id: int, name: str) -> None:
        """Имя занято в этом наборе — отказ, а не чужое исключение наверх."""
        await self._written(
            update(tag_table).where(tag_table.c.id == tag_id)
            .values(name=capitalized(name)),
            TagExists(f"{name} уже заведён"),
        )

    async def usage(self, tag_id: int) -> int:
        """Сколько карточек носит этот тег.

        Нужно удалению: у тега с носителями оно спрашивает подтверждение и
        называет их число, а ничей тег уходит молча — терять там нечего."""
        row = await self._row(
            select(func.count())
            .select_from(item_tag_table)
            .where(item_tag_table.c.tag_id == tag_id)
        )
        return row.count

    async def delete(self, tag_id: int) -> None:
        await self._run(delete(tag_table).where(tag_table.c.id == tag_id))

    async def assign(self, item_id: int, tag_id: int) -> None:
        """Тег чужого набора на карточку не вешается. Держит это репозиторий, а
        не база: `item.kind` в `item_tag` нет."""
        async with self._sessions() as session:
            kinds = await session.execute(
                select(item_table.c.kind, tag_table.c.kind.label("tag_kind"))
                .select_from(item_table)
                .join(tag_table, tag_table.c.id == tag_id, isouter=True)
                .where(item_table.c.id == item_id)
            )
            row = kinds.one_or_none()
            if row is None or row.tag_kind is None or row.kind != row.tag_kind:
                raise WrongTagKind(f"тег {tag_id} не для карточки {item_id}")

            await session.execute(
                insert(item_tag_table)
                .values(item_id=item_id, tag_id=tag_id)
                .on_conflict_do_nothing()
            )
            await session.commit()

    async def unassign(self, item_id: int, tag_id: int) -> None:
        await self._run(
            delete(item_tag_table).where(
                item_tag_table.c.item_id == item_id,
                item_tag_table.c.tag_id == tag_id,
            )
        )

    async def tags_of(self, item_id: int) -> list[Tag]:
        return await self._mapped(
            select(tag_table.c.id, tag_table.c.name)
            .join(item_tag_table, item_tag_table.c.tag_id == tag_table.c.id)
            .where(item_tag_table.c.item_id == item_id)
            .order_by(tag_table.c.position),
            to_tag,
        )
