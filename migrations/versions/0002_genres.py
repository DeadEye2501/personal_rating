"""Справочник жанров и правила, ведущие к ним.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-29

Сами наборы и соответствия лежат данными в `migrations/reference/`: справочник
правят глазами, и в одном файле с кодом записи он бы туда не поместился.

Здесь только перенос объявленного в базу. Поимённо соответствия сторожит
`tests/backend/test_genre_reference.py`: он сверяет объявленное с записанным
эталоном.
"""

import sqlalchemy as sa
from alembic import op

from migrations.reference.gog import GOG
from migrations.reference.names import FILM, GAME
from migrations.reference.old_games import OLD_GAMES
from migrations.reference.steam import STEAM
from migrations.reference.tmdb import TMDB

revision: str = "0002"
down_revision: str | None = "0001"

BOOKS = (
    ("tmdb", TMDB, "film"),
    ("steam", STEAM, "game"),
    ("gog", GOG, "game"),
    ("old_games", OLD_GAMES, "game"),
)


def upgrade() -> None:
    connection = op.get_bind()

    ids: dict[tuple[str, str], int] = {}
    for kind, names in (("film", FILM), ("game", GAME)):
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
            _marks(connection, result.lastrowid, rule)


def _marks(connection, rule_id: int, rule) -> None:
    for forbidden, ext_ids in ((False, rule.required()), (True, rule.forbidden())):
        for ext_id in ext_ids:
            connection.execute(
                sa.text(
                    "INSERT INTO genre_rule_mark (rule_id, ext_id, forbidden) "
                    "VALUES (:rule_id, :ext_id, :forbidden)"
                ),
                {"rule_id": rule_id, "ext_id": ext_id, "forbidden": forbidden},
            )


def downgrade() -> None:
    # Правила уходят каскадом вслед за жанром, метки — вслед за правилом:
    # внешние ключи в миграциях включены.
    connection = op.get_bind()
    connection.execute(sa.text("DELETE FROM genre"))
