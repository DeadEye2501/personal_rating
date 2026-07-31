"""Страница, ресурсы и обложки по HTTP.

Своё, а не файловый сервер pywebview, по трём замеренным причинам: корень `/` у
него отвечает `500`, `.woff2` уезжает как `text/html`, а ручки обложки нет
вовсе. Сам сервер при этом поднимает pywebview: окну отдаётся WSGI-приложение,
и оно оказывается нашим."""

import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs

from backend.model import Source
from bridge.thread import DEADLINE

logger = logging.getLogger(__name__)

# `bridge/serve.py` лежит в `bridge/`, а собирает фронт Vite в `client/dist` —
# отсюда шаг наверх. Под заморозкой корень другой, но появляется он только
# вместе со сборкой одним файлом.
WEB_ROOT = Path(__file__).resolve().parent.parent / "client" / "dist"

# Тип объявляем сами: у `mimetypes` этой машины `.woff2` нет, и браузер получил
# бы `text/html`. Модуль с неверным типом Chromium не исполнит вовсе.
TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
    ".woff2": "font/woff2",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".webp": "image/webp",
}

# Тип картинки берётся из первых байтов: хранилище держит только байты, а
# `Pillow` в клиент не пускает граница слоёв.
MAGIC = ((b"\x89PNG\r\n\x1a\n", "image/png"),
         (b"\xff\xd8\xff", "image/jpeg"),
         (b"RIFF", "image/webp"))


class Page:
    """Дерево отдаётся одно и целиком; всё, что не `/poster`, — это файл."""

    def __init__(self, thread, root: Path = WEB_ROOT) -> None:
        self._thread = thread
        self._root = Path(root).resolve()

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "/")
        if path == "/poster":
            return self._poster(parse_qs(environ.get("QUERY_STRING", "")),
                                start_response)
        return self._file(path, start_response)

    def _file(self, path: str, start_response):
        if not self._root.is_dir():
            # Фронт не собран: окно откроется пустым, и без этой записи оно
            # молчит о причине — а причина ровно одна и чинится одной командой.
            logger.error("нет собранного фронта: %s", self._root)
            return _answer(start_response, "404 Not Found", "text/plain", b"")
        wanted = "index.html" if path == "/" else path.lstrip("/")
        # Проверка по разрешённому пути, а не по строке: `..` внутри имени файла
        # — законный символ, а вот выход за корень отдавать нельзя.
        resolved = (self._root / wanted).resolve()
        if not resolved.is_relative_to(self._root):
            return _answer(start_response, "403 Forbidden", "text/plain", b"")
        if not resolved.is_file():
            return _answer(start_response, "404 Not Found", "text/plain", b"")
        try:
            body = resolved.read_bytes()
        except OSError:
            # Под заморозкой pywebview подменяет `stderr` на пустоту, и
            # непойманное здесь дало бы пустое окно без единой строки в логе.
            logger.exception("файл страницы не прочитался: %s", resolved)
            return _answer(start_response, "404 Not Found", "text/plain", b"")
        kind = TYPES.get(resolved.suffix, "application/octet-stream")
        return _answer(start_response, "200 OK", kind, body)

    def _poster(self, query: dict, start_response):
        item = _single(query, "item")
        source = _single(query, "source")
        url = _single(query, "url")
        # Номер разбирается здесь: нечисловой — это поломка страницы, а не
        # отсутствие обложки, и отдав на него 404, мы спрятали бы её за
        # нормальным исходом. Заодно дальше по пути `int()` уже не нужен.
        number = int(item) if item and item.isdigit() else None
        if number is None and not (source and url):
            return _answer(start_response, "400 Bad Request", "text/plain", b"")

        try:
            picture = self._thread.run(
                lambda back: _fetched(back, number, source,
                                      url)).result(DEADLINE)
        except Exception:
            logger.exception("обложка не доехала")
            return _answer(start_response, "404 Not Found", "text/plain", b"")
        if not isinstance(picture, bytes | bytearray) or not picture:
            # Не приехала, отказал источник, пустые байты — на месте обложки
            # заглушка, и делает её `onerror` у картинки.
            return _answer(start_response, "404 Not Found", "text/plain", b"")
        # Прокрутка ленты спрашивает одну и ту же обложку по многу раз, и без
        # кеша каждая перерисовка тащила бы все постеры заново — по потоку
        # моста и чтению второго файла базы на карточку.
        #
        # Адрес при этом от содержимого не зависит, и перезалитую свою обложку
        # браузер до конца сессии не спросит. Сбрасывает кеш сторона, которая
        # знает о перезаливке, — окно карточки: оно дописывает к адресу метку
        # момента. Здесь этого не сделать: обработчик не знает, что изменилось.
        return _answer(start_response, "200 OK", _looks_like(picture), picture,
                       cache="max-age=86400")


async def _fetched(back, item, source, url):
    """У своей карточки источник и адрес берутся из неё самой: страница знает
    только номер, а подсказке при вводе имени больше и не из чего исходить.
    У кандидата номера нет вовсе — обложку тогда не сохраняем."""
    if item is None:
        return await back.posters.poster_for(None, Source(source), url,
                                             datetime.now())
    card = await back.library.get(item)
    if card is None:
        return None
    return await back.posters.poster_for(card.id, card.source,
                                         card.poster_url, datetime.now())


def _looks_like(picture: bytes) -> str:
    for magic, kind in MAGIC:
        if picture.startswith(magic):
            return kind
    return "application/octet-stream"


def _single(query: dict, name: str) -> str | None:
    values = query.get(name)
    return values[0] if values else None


def _answer(start_response, status: str, kind: str, body: bytes,
            cache: str | None = None):
    headers = [("Content-Type", kind), ("Content-Length", str(len(body)))]
    if cache:
        headers.append(("Cache-Control", cache))
    start_response(status, headers)
    return [body]
