import os
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine, event, pool

from backend.config import load_config
from backend.storage.session import prepare_connection
from backend.storage.tables import metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = metadata


def database_path() -> Path:
    # `-x db=<путь>` нужен тестам: они гоняют миграции по временному файлу.
    override = context.get_x_argument(as_dictionary=True).get("db")
    if override:
        return Path(override)
    settings = load_config(os.environ, base_dir=Path(__file__).resolve().parents[1])
    return settings.library_db


def database_url() -> str:
    # Alembic ходит синхронным драйвером, приложение — асинхронным: разница
    # только в префиксе. Папку под базу заводим здесь — родная create_engine
    # её не создаёт и падает с «unable to open database file».
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path}"


def migrate() -> None:
    engine = create_engine(database_url(), poolclass=pool.NullPool)

    # Соединение готовится слушателем, а не запросом на нём: любой execute
    # открывает транзакцию, Alembic считает её внешней и перестаёт коммитить
    # сам — миграции проходят, а данные откатываются, и alembic_version
    # остаётся пустым.
    @event.listens_for(engine, "connect")
    def prepare(dbapi_connection, _record):
        prepare_connection(dbapi_connection)

    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


migrate()
