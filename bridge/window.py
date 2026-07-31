"""Окно приложения и проверка того, чем оно рисует."""

import logging

import webview

from bridge.api import Api
from bridge.serve import Page

logger = logging.getLogger(__name__)

TITLE = "Personal Rating"

# Системный WebView2 — тот самый Chromium, в котором рисовался макет. Список
# разрешённого, а не запрещённого: седьмой движок обязан упереться в проверку.
RENDERER = "edgechromium"

# Ширина шапки — минимум окна; максимум не ограничен. Число уточнится, когда
# шапка появится и её ширину станет чем замерить.
MIN_WIDTH = 900
MIN_HEIGHT = 600

# Стартовый размер задан явно: умолчание `create_window` — 800×600, то есть
# меньше собственного минимума, и окно открывалось бы уже подтянутым.
WIDTH = 1280
HEIGHT = 820

# Цвет до отрисовки страницы, единственный, который окно показывает само. Обязан
# совпасть с фоном палитры — иначе каждый запуск начинается со вспышки.
BACKGROUND = "#0a0a0a"


def supported(renderer: str | None) -> bool:
    return renderer == RENDERER


def open_window(thread, debug: bool = False) -> None:
    """Возвращается только после закрытия окна: `webview.start` блокирует."""
    webview.create_window(
        TITLE,
        url=Page(thread),
        js_api=Api(thread),
        width=WIDTH,
        height=HEIGHT,
        min_size=(MIN_WIDTH, MIN_HEIGHT),
        background_color=BACKGROUND,
    )
    webview.start(func=_check_renderer, debug=debug)
    # Окно закрыли — гасим начатое и закрываем бэкенд. Отдельного флага
    # «мы закрываемся» не заводим: список живых задач ведёт поток.
    thread.close()


def _check_renderer() -> None:
    """Зовётся фоновой функцией: к этому моменту библиотека уже выбрала движок."""
    if not supported(webview.renderer):
        logger.critical(
            "окно рисует %s вместо %s: среда WebView2 не установлена, и "
            "оформление работать не будет", webview.renderer, RENDERER)
