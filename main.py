"""Собирает зависимости, настраивает лог и поднимает окно."""

import logging
import logging.handlers
import os
from pathlib import Path

from dotenv import load_dotenv

from backend.app import build_backend
from backend.config import load_config
from bridge.thread import BackendThread
from bridge.window import open_window

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent

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
    load_dotenv()
    config = load_config(os.environ, BASE_DIR)
    setup_logging(config)

    # Сборка уезжает функцией: бэкенд обязан родиться внутри чужого потока —
    # движок SQLAlchemy привязан к циклу, в котором создан, — а импортировать
    # `backend.app` из `bridge/` нельзя: там стоит сторож границы слоёв, и с
    # ним приехали бы и SQLAlchemy, и httpx в поток интерфейса.
    thread = BackendThread(lambda: build_backend(config))
    try:
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
