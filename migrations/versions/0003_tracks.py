"""Треки альбома и справочник жанров книг и музыки.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-22

Две вещи в одной ревизии нарочно: обе нужны новым типам содержимого, и разлить
их порознь значило бы применить половину справочника, а вторую везти следующей
ревизией. Решение пользователя 22.08.2026.

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

from migrations.reference.deezer import DEEZER
from migrations.reference.google_books import GOOGLE_BOOKS
from migrations.reference.names import BOOK, MUSIC

revision: str = "0003"
down_revision: str | None = "0002"

# Тем же порядком и теми же именами, что в `0002`: сторож справочника читает
# `BOOKS` у обеих ревизий одинаково.
BOOKS = (
    ("google_books", GOOGLE_BOOKS, "book"),
    ("deezer", DEEZER, "music"),
)


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
    _seed_genres(op.get_bind())


def _seed_genres(connection) -> None:
    """Имена жанров и правила перевода чужих меток в них.

    Своей копией, а не вызовом `0002`: миграция обязана оставаться
    самодостаточной. Позови она соседнюю — правка соседней меняла бы уже
    применённую ревизию, а это ровно то, от чего наслаивание и заведено.

    Копия при этом неполная, и нарочно: `0002` пишет ещё и запрещающие метки, а
    здесь их не бывает. У обоих справочников условий нет вовсе — метка означает
    жанр сама по себе, как у TMDB, — и ветка `forbidden` осталась бы без
    сегодняшнего потребителя. Появится правило с запретом — вернётся и она."""
    ids: dict[tuple[str, str], int] = {}
    for kind, names in (("book", BOOK), ("music", MUSIC)):
        for name in names:
            result = connection.execute(
                sa.text("INSERT INTO genre (name, kind) VALUES (:name, :kind)"),
                {"name": name, "kind": kind},
            )
            ids[(kind, name)] = result.lastrowid

    for source, rules, kind in BOOKS:
        for rule in rules:
            result = connection.execute(
                sa.text(
                    "INSERT INTO genre_rule (source, genre_id, alone) "
                    "VALUES (:source, :genre_id, :alone)"
                ),
                {"source": source, "genre_id": ids[(kind, rule.genre)],
                 "alone": rule.alone},
            )
            for ext_id in rule.required():
                connection.execute(
                    sa.text(
                        "INSERT INTO genre_rule_mark (rule_id, ext_id, forbidden) "
                        "VALUES (:rule_id, :ext_id, 0)"
                    ),
                    {"rule_id": result.lastrowid, "ext_id": ext_id},
                )


def downgrade() -> None:
    # Правила уходят каскадом вслед за жанром, метки — вслед за правилом.
    connection = op.get_bind()
    connection.execute(
        sa.text("DELETE FROM genre WHERE kind IN ('book', 'music')"))
    op.drop_table("track")
