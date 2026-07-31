"""Решение по рендереру и настройка лога. Окно здесь не поднимается ни разу."""

import logging
import subprocess
import sys
from pathlib import Path

import pytest
import webview

from bridge.api import Api
from bridge.serve import Page
from bridge.thread import Closed
from bridge.window import (
    BACKGROUND,
    MIN_HEIGHT,
    MIN_WIDTH,
    RENDERER,
    _check_renderer,
    open_window,
    supported,
)


def test_the_system_chromium_is_what_we_drew_the_mockup_in():
    assert supported("edgechromium")


def test_the_old_engine_is_not_silently_accepted():
    """Нет среды WebView2 — pywebview молча уезжает на MSHTML, и приложение
    просто выглядит сломанным. Молчание тут хуже отказа."""
    assert not supported("mshtml")


def test_an_unknown_engine_is_not_accepted():
    """Список разрешённого, а не список запрещённого: седьмой движок обязан
    упереться в проверку, а не проскочить."""
    assert not supported("qtwebengine")
    assert not supported(None)


def test_a_foreign_engine_leaves_a_line_in_the_log(monkeypatch, caplog):
    """Единственное, что отличает «нет среды WebView2» от «приложение просто
    выглядит сломанным». Критерий приёмки — **отсутствие** этой строки в логе,
    поэтому сломанная проверка выглядит точно как исправный движок."""
    monkeypatch.setattr(webview, "renderer", "mshtml", raising=False)

    with caplog.at_level(logging.CRITICAL):
        _check_renderer()

    assert "mshtml" in caplog.text
    assert RENDERER in caplog.text


def test_our_own_engine_says_nothing(monkeypatch, caplog):
    """Молчание — это ответ «всё в порядке», и оно обязано быть настоящим."""
    monkeypatch.setattr(webview, "renderer", RENDERER, raising=False)

    with caplog.at_level(logging.CRITICAL):
        _check_renderer()

    assert caplog.text == ""


def test_the_log_reaches_its_file(tmp_path):
    """Настройка лога проверяется отдельным процессом: `basicConfig` меняет
    корень, а под pytest корень уже занят перехватчиком — в общем прогоне
    проверка молча ничего бы не настроила.

    Свойство наблюдается по следствию: строка обязана доехать до файла. На
    записи в этот файл висит вся диагностика приложения, включая ту, которой
    ловят чужой движок."""
    code = (
        "import logging, os, sys;"
        "sys.path.insert(0, r'.');"
        "from pathlib import Path;"
        "from backend.config import load_config;"
        "from main import setup_logging;"
        f"config = load_config({{'DATA_DIR': r'{tmp_path}'}}, Path('.'));"
        "setup_logging(config);"
        "logging.getLogger('проба').critical('строка дошла')"
    )

    subprocess.run([sys.executable, "-c", code], check=True, cwd=Path.cwd())

    written = (tmp_path / "app.log").read_text(encoding="utf-8")
    assert "строка дошла" in written


def test_the_window_gets_the_bridge_and_our_own_page(spy, monkeypatch):
    """Сборка — самое дырявое место проекта, и это уже третий раз: подмена моста
    отдачей страницы, перепутанный минимальный размер и пропавшее закрытие
    потока прошли бы при полностью зелёном наборе.

    Окно здесь не поднимается: обе стороны pywebview подменены."""
    seen = {}
    monkeypatch.setattr(webview, "create_window",
                        lambda title, **rest: seen.update(rest, title=title))
    monkeypatch.setattr(webview, "start", lambda **rest: seen.update(start=rest))
    closed = []
    monkeypatch.setattr(spy, "close", lambda: closed.append(True))

    open_window(spy)

    assert isinstance(seen["js_api"], Api)
    assert isinstance(seen["url"], Page)
    assert seen["min_size"] == (MIN_WIDTH, MIN_HEIGHT)
    assert seen["background_color"] == BACKGROUND
    # Проверку движка ставит `start`: к моменту вызова библиотека уже выбрала,
    # чем рисует, а до него смотреть не на что.
    assert seen["start"]["func"] is _check_renderer
    # Закрытие идёт после того, как окно закрылось: `start` блокирует.
    assert closed == [True]


def test_closing_the_window_closes_the_backend(spy, monkeypatch):
    """Иначе процесс переживает окно: поток бэкенда держит цикл, соединения и
    начатые запросы."""
    monkeypatch.setattr(webview, "create_window", lambda title, **rest: None)
    monkeypatch.setattr(webview, "start", lambda **rest: None)

    open_window(spy)

    # Наблюдается следствием: закрытый поток заявок больше не принимает.
    with pytest.raises(Closed):
        spy.run(lambda back: back.tags.list_for_kind(None))
