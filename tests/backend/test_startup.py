"""Запуск готовит рабочую папку сам: папка, файл настроек и схема базы.

Решение пользователя 03.08.2026: «exe ДОЛЖЕН быть самодостаточным и сам
создавать все нужные файлы баз при первом старте». Спека —
`docs/specs/2026-08-03-delivery.md`.
"""

import logging
from dataclasses import fields
from pathlib import Path

import sqlalchemy

from backend.config import Config, load_config
from backend.startup import TEMPLATE_NAME, ensure_env, upgrade_schema

ROOT = Path(__file__).resolve().parents[2]
SHORT = "TMDB_API_KEY=\nLOG_LEVEL=INFO\n"


def a_template(folder: Path) -> Path:
    template = folder / "шаблон"
    template.write_text(SHORT, encoding="utf-8")
    return template


def test_the_working_folder_is_created(tmp_path):
    """Папки может не быть вовсе: рядом с распакованным `.exe` нет ничего."""
    ensure_env(tmp_path / "data", a_template(tmp_path))

    assert (tmp_path / "data").is_dir()


def test_the_settings_file_is_written_from_the_template(tmp_path):
    """Переменные с пояснениями человек заполняет руками, и взяться им неоткуда,
    кроме шаблона.

    Из шаблона, а не из своего списка в коде: второй список разошёлся бы с
    первым молча, и в созданном файле не хватало бы переменной — а узнал бы об
    этом человек только по неработающему источнику."""
    ensure_env(tmp_path / "data", a_template(tmp_path))

    assert (tmp_path / "data" / ".env").read_text(encoding="utf-8") == SHORT


def test_an_existing_settings_file_is_left_alone(tmp_path):
    """Заполненные ключи затирать нельзя ни при каком запуске: восстановить их
    человеку неоткуда."""
    folder = tmp_path / "data"
    folder.mkdir()
    (folder / ".env").write_text("TMDB_API_KEY=мой ключ\n", encoding="utf-8")

    ensure_env(folder, a_template(tmp_path))

    assert (folder / ".env").read_text(encoding="utf-8") == "TMDB_API_KEY=мой ключ\n"


def test_a_missing_template_does_not_stop_the_start(tmp_path):
    """Шаблон лежит файлом рядом с программой, и его может не оказаться —
    например, забыли положить в сборку. Приложение обязано подняться и без него:
    без ключей работают игры и вся своя библиотека, а без папки — ничего."""
    ensure_env(tmp_path / "data", tmp_path / "нет такого файла")

    assert (tmp_path / "data").is_dir()
    assert not (tmp_path / "data" / ".env").exists()


def test_the_template_names_every_variable_the_settings_read():
    """Сторож от расхождения: шаблон и `load_config` — две стороны одного
    уговора, разъехаться они могут молча, и цена этому — переменная, которую
    человек не увидит и не заполнит.

    Имена берутся из самого шаблона и подставляются метками: поле настройки,
    оставшееся пустым, и значит «эту переменную читают, а в шаблоне её нет».
    Списка имён в проверке нет нарочно — он расходился бы не с ожидаемым, а сам
    с собой."""
    named = _variables_of((ROOT / TEMPLATE_NAME).read_text(encoding="utf-8"))
    marks = {name: f"<{name}>" for name in named}

    settings = load_config(marks, base_dir=ROOT)

    unnamed = [one.name for one in fields(Config)
               if isinstance(getattr(settings, one.name), str)
               and not getattr(settings, one.name).startswith("<")]
    assert unnamed == []


def test_the_schema_comes_from_the_migrations(tmp_path, monkeypatch):
    """Схему поднимают миграции, а не объявления таблиц: справочник жанров живёт
    в самой миграции, и `create_all` завёл бы пустые таблицы.

    Наблюдается справочник, а не список таблиц: пустая схема — тоже схема, и по
    ней «миграции прошли» неотличимо от «таблицы объявлены»."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))

    upgrade_schema()

    assert _genres_in(tmp_path / "library.db") > 0


def test_the_next_start_leaves_the_base_alone(tmp_path, monkeypatch):
    """Миграции гоняются на каждом запуске, а не только на первом: узнать,
    первый ли он, можно только спросив саму базу, а это и делает alembic.

    Наблюдается справочник, а не факт «не упало»: пересозданная с нуля база
    прошла бы проверку на существование файла."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    upgrade_schema()
    engine = sqlalchemy.create_engine(f"sqlite:///{tmp_path / 'library.db'}")
    with engine.begin() as connection:
        connection.execute(sqlalchemy.text("delete from genre where id > 1"))
    engine.dispose()

    upgrade_schema()

    assert _genres_in(tmp_path / "library.db") == 1


def test_the_migrations_do_not_touch_the_application_log(tmp_path, monkeypatch):
    """Alembic в своём `env.py` зовёт `fileConfig`, а тот переконфигурирует
    корневой логгер и **глушит все существующие**: `disable_existing_loggers`
    у него истина по умолчанию.

    Запущенный отдельным процессом, он этим никому не мешал. Внутри приложения
    он стирает лог, настроенный строкой выше, — и приложение продолжает
    работать молча, что и есть худший исход для того, кто потом ищет причину."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    mine = logging.getLogger("тестовый")

    upgrade_schema()

    assert mine.isEnabledFor(logging.WARNING)


def _genres_in(path: Path) -> int:
    engine = sqlalchemy.create_engine(f"sqlite:///{path}")
    try:
        with engine.begin() as connection:
            return connection.execute(
                sqlalchemy.text("select count(*) from genre")).scalar()
    finally:
        engine.dispose()


def _variables_of(text: str) -> set[str]:
    return {line.split("=", 1)[0].strip() for line in text.splitlines()
            if "=" in line and not line.lstrip().startswith("#")}
