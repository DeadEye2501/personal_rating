"""Схема из миграций против схемы из объявлений."""

from pathlib import Path

from sqlalchemy import create_engine, inspect, text

from backend.storage.tables import metadata
from tests.alembic_runner import alembic
from tests.conftest import TABLES

# Alembic заводит её сам и в схему проекта не входит.
STAMP = "alembic_version"


def declared(db_path: Path) -> None:
    """База, поднятая прямо из объявлений, — эталон для сверки с миграцией."""
    engine = create_engine(f"sqlite:///{db_path}")
    metadata.create_all(engine)
    engine.dispose()


def table_shape(inspector, name: str) -> dict:
    """Всё о таблице, что видно снаружи: не только имена колонок."""
    return {
        "columns": [
            (column["name"], str(column["type"]), column["nullable"])
            for column in inspector.get_columns(name)
        ],
        "primary_key": inspector.get_pk_constraint(name)["constrained_columns"],
        # Имена ограничений — часть схемы, а не украшение: SQLite меняет её
        # пересозданием таблицы, и Alembic ищет ограничение по имени.
        "primary_key_name": inspector.get_pk_constraint(name)["name"],
        "unique": sorted(
            (one["name"], tuple(one["column_names"]))
            for one in inspector.get_unique_constraints(name)
        ),
        "indexes": sorted(
            (one["name"], tuple(one["column_names"]), one["unique"])
            for one in inspector.get_indexes(name)
        ),
        "foreign_keys": sorted(
            (
                one["name"],
                tuple(one["constrained_columns"]),
                one["referred_table"],
                (one.get("options") or {}).get("ondelete"),
            )
            for one in inspector.get_foreign_keys(name)
        ),
    }


def shape(db_path: Path) -> dict:
    """Снимок всей базы: таблица за таблицей, кроме служебной alembic_version."""
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.connect() as connection:
        inspector = inspect(connection)
        found = {
            name: table_shape(inspector, name)
            for name in sorted(inspector.get_table_names())
            if name != STAMP
        }
    engine.dispose()
    return found


def stamped(db_path: Path) -> list[str]:
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.connect() as connection:
        found = connection.execute(
            text(f"SELECT version_num FROM {STAMP}")
        ).scalars().all()
    engine.dispose()
    return found


def test_upgrade_builds_the_whole_schema(tmp_path):
    # Путь нарочно вложенный: каталога данных при первом запуске ещё нет, и
    # env.py обязан его завести — иначе «unable to open database file».
    db_path = tmp_path / "data" / "library.db"
    alembic(db_path, "upgrade", "head")

    assert set(shape(db_path)) == TABLES


def test_version_is_stamped_and_a_rerun_is_quiet(tmp_path):
    """Ловушка, из-за которой миграции проходят вхолостую: если env.py открыл
    транзакцию до context.configure, Alembic считает её внешней и не коммитит.
    Таблицы при этом создаются (DDL идёт автокоммитом), а alembic_version
    остаётся пустым — и второй запуск валится на «table already exists»."""
    db_path = tmp_path / "library.db"
    alembic(db_path, "upgrade", "head")

    assert stamped(db_path), "alembic_version пуст — миграции откатились"

    alembic(db_path, "upgrade", "head")   # повторный прогон обязан пройти начисто


def test_downgrade_takes_the_schema_back_out(tmp_path):
    """Обратный ход — единственный способ вернуть базу к пустой, если миграция
    поехала не туда. Проверяется прогоном: пропущенный `drop_table` виден
    только тем, что таблица осталась."""
    db_path = tmp_path / "library.db"
    alembic(db_path, "upgrade", "head")
    alembic(db_path, "downgrade", "base")

    assert shape(db_path) == {}
    assert not stamped(db_path)

    alembic(db_path, "upgrade", "head")   # и обратно, начисто
    assert set(shape(db_path)) == TABLES


def test_migration_matches_the_declared_tables(tmp_path):
    """Схема из миграций и схема из tables/ не должны разъезжаться.

    Сверяются две поднятые базы целиком, а не списки имён: потерянный индекс,
    снятый каскад, суженный ключ уникальности и подменённый тип колонки имена
    не меняют и при сверке по именам проходят молча. Сверка в обе стороны:
    лишняя таблица в миграции — такое же расхождение, как недостающая."""
    migrated = tmp_path / "migrated.db"
    alembic(migrated, "upgrade", "head")
    reference = tmp_path / "declared.db"
    declared(reference)

    assert shape(migrated) == shape(reference)
