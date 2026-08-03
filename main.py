"""Собирает зависимости, настраивает лог и поднимает окно."""

import logging
import logging.handlers
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from backend.app import build_backend
from backend.config import load_config
from backend.startup import TEMPLATE_NAME, ensure_env, upgrade_schema
from bridge.thread import BackendThread
from bridge.window import open_window

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent

# Куда класть данные. Под заморозкой `BASE_DIR` — это временная папка, куда
# распаковался бандл: она стирается при выходе, и база с ключами исчезала бы
# вместе с ней. Рядом с самим `.exe` — решение пользователя 03.08.2026.
HOME = Path(sys.executable).parent if getattr(sys, "frozen", False) else BASE_DIR

# Лог лежит рядом с программой и не растёт бесконечно.
LOG_BYTES = 5 * 1024 * 1024
LOG_FILES = 3


def setup_logging(config) -> None:
    config.log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=config.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.handlers.RotatingFileHandler(
                config.log_file, maxBytes=LOG_BYTES, backupCount=LOG_FILES,
                encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def main() -> None:
    # Порядок здесь и есть содержание: папка заводится до файла настроек, файл
    # читается до схемы — путь к базе alembic берёт из тех же настроек, — и всё
    # это до окна, потому что первый же его запрос идёт в базу.
    #
    # Корневой `.env` читается первым и побеждает: он у разработчика, а рабочий
    # лежит в папке данных. `load_dotenv` уже прочитанного не перебивает.
    load_dotenv()
    folder = load_config(os.environ, HOME).data_dir
    ensure_env(folder, BASE_DIR / TEMPLATE_NAME)
    load_dotenv(folder / ".env")

    config = load_config(os.environ, HOME)
    # Alembic поднимает схему своим процессом и путь к базе берёт из окружения.
    # Без этой строки под заморозкой он взял бы своё умолчание — временную папку
    # бандла, — и приложение читало бы пустую базу рядом с exe.
    os.environ["DATA_DIR"] = str(config.data_dir)
    setup_logging(config)

    # Сборка уезжает функцией: бэкенд обязан родиться внутри чужого потока —
    # движок SQLAlchemy привязан к циклу, в котором создан, — а импортировать
    # `backend.app` из `bridge/` нельзя: там стоит сторож границы слоёв, и с
    # ним приехали бы и SQLAlchemy, и httpx в поток интерфейса.
    thread = BackendThread(lambda: build_backend(config))
    try:
        # Первое, что нужно знать при разборе: куда уехали файлы. `DATA_DIR`
        # разводит настройки и данные по разным папкам, и без этой строки
        # перенесённая папка выглядела бы обычным первым запуском.
        logger.info("настройки %s, данные %s", folder / ".env", config.data_dir)

        # Схема поднимается внутри `try`, а не до него: битая база, база от
        # будущей версии и недоступная папка — обычные исходы, и без записи они
        # дают ровно то, что комментарий ниже объявляет недопустимым.
        upgrade_schema(BASE_DIR)
        thread.start()
        open_window(thread, debug=bool(os.environ.get("PR_DEBUG")))
    except Exception:
        # Под заморозкой `stderr` подменён на пустоту, и непойманное здесь
        # означало бы: окно не открылось, лог пуст, на экране ничего.
        logger.exception("приложение не поднялось")
        raise
    finally:
        # Закрытие идёт и по обычному пути, изнутри `open_window`; второй раз
        # оно молчит, а вот сорвавшийся запуск иначе оставил бы поток жить.
        thread.close()


if __name__ == "__main__":
    main()
