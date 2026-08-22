"""Треки альбома отдельной таблицей.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-22

Первая ревизия, положенная поверх, а не переписавшая соседнюю: правило
«миграции не наслаиваются» держалось оговоркой «пока в базе нет ничего, что
жалко потерять», а в базе теперь настоящие оценки.

Трек не человек и не студия, поэтому в таблицу титров он не кладётся: она ведёт
в `person`, откуда имена идут в подсказку при вводе и в поиск «все работы этого
человека». У альбома название трека совпадает с именем исполнителя сплошь и
рядом, и они склеились бы в одну строку.
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"


def upgrade() -> None:
    op.create_table(
        "track",
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["item.id"],
                                name=op.f("fk_track_item_id"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("item_id", "position", name=op.f("pk_track")),
    )


def downgrade() -> None:
    op.drop_table("track")
