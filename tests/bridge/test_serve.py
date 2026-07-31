"""Отдача страницы, ресурсов и обложек.

WSGI зовётся напрямую: сервер здесь не поднимается, окно не создаётся."""

from datetime import datetime

from backend.model import Item, Kind, Reason, Refusal, Source
from bridge.serve import Page

PNG = b"\x89PNG\r\n\x1a\nthe rest"
JPEG = b"\xff\xd8\xff\xe0the rest"
CANDIDATE = "source=tmdb&url=https%3A%2F%2Fimage%2F1.jpg"


def call(page, path, query=""):
    seen = {}

    def start(status, headers):
        seen["status"] = status
        seen["headers"] = dict(headers)

    body = b"".join(page({"PATH_INFO": path, "QUERY_STRING": query,
                          "REQUEST_METHOD": "GET"}, start))
    return seen["status"], seen["headers"], body


def test_the_root_gives_the_page(tmp_path, spy):
    """У сервера pywebview корень отвечает `500` — замерено. Свой обязан
    отдавать страницу."""
    (tmp_path / "index.html").write_bytes(b"<h1>\xd1\x82\xd1\x83\xd1\x82</h1>")

    status, headers, body = call(Page(spy, tmp_path), "/")

    assert status.startswith("200")
    assert headers["Content-Type"].startswith("text/html")
    assert body == b"<h1>\xd1\x82\xd1\x83\xd1\x82</h1>"
    # Длину WebView2 берёт на веру и режет по ней: соврав, мы отдали бы модуль
    # Vite обрезанным, и страница осталась бы пустой без единой ошибки.
    assert headers["Content-Length"] == str(len(body))
    # Разметка и сборка меняются с каждой правкой фронта, и сутки старого
    # `index.html` означали бы сутки старого приложения.
    assert "Cache-Control" not in headers


def test_a_font_gets_its_own_type(tmp_path, spy):
    """В `mimetypes` этой машины `.woff2` нет, и файловый сервер библиотеки
    отдаёт его как `text/html` — замерено."""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "roboto.woff2").write_bytes(b"wOF2")

    _, headers, _ = call(Page(spy, tmp_path), "/assets/roboto.woff2")

    assert headers["Content-Type"] == "font/woff2"


def test_a_module_gets_the_script_type(tmp_path, spy):
    """Chromium не исполнит модуль с неверным типом, и страница останется
    пустой без единой ошибки."""
    (tmp_path / "app.js").write_bytes(b"export {}")

    _, headers, _ = call(Page(spy, tmp_path), "/app.js")

    assert headers["Content-Type"].startswith("text/javascript")


def test_an_unknown_extension_travels_as_bytes(tmp_path, spy):
    """Своя таблица типов знает восемь расширений, а сборка кладёт рядом и
    `.map`, и `.json`: неизвестное обязано уехать потоком байтов, а не уронить
    отдачу."""
    (tmp_path / "app.js.map").write_bytes(b"{}")

    status, headers, _ = call(Page(spy, tmp_path), "/app.js.map")

    assert status.startswith("200")
    assert headers["Content-Type"] == "application/octet-stream"


def test_a_way_out_of_the_root_is_refused(tmp_path, spy):
    """Отдаём только своё дерево, и проверка идёт по разрешённому пути, а не по
    строке: `..` внутри имени файла — законный символ."""
    (tmp_path.parent / "чужое.txt").write_bytes(b"\xd1\x81\xd0\xb5\xd0\xba")

    status, _, body = call(Page(spy, tmp_path), "/../чужое.txt")

    assert status.startswith("403")
    assert body == b""


def test_a_missing_file_is_not_found(tmp_path, spy):
    status, _, _ = call(Page(spy, tmp_path), "/нет.js")
    assert status.startswith("404")


def test_a_cover_of_a_library_card_is_taken_by_its_number(tmp_path, spy, asked):
    """Источник и адрес берёт сам обработчик: страница знает только `item_id`,
    и подсказке при вводе имени больше и не из чего исходить."""
    answers, log = asked
    answers["library.get"] = Item(id=12, kind=Kind.MOVIE, source=Source.TMDB,
                                  source_id="1", title="Одиссея",
                                  synced_at=datetime(2026, 7, 31),
                                  poster_url="https://image/1.jpg")
    answers["posters.poster_for"] = PNG

    status, headers, body = call(Page(spy, tmp_path), "/poster", "item=12")

    assert status.startswith("200")
    assert headers["Content-Type"] == "image/png"
    assert headers["Cache-Control"] == "max-age=86400"
    assert body == PNG
    assert [name for name, _, _ in log] == ["library.get", "posters.poster_for"]
    _, args, _ = log[1]
    assert args[:3] == (12, Source.TMDB, "https://image/1.jpg")
    # Часы подставляет мост, как и везде: без момента строка обложки не
    # запишется вовсе — `fetched_at` в базе обязательный.
    assert isinstance(args[3], datetime)


def test_a_cover_of_a_candidate_is_taken_by_its_address(tmp_path, spy, asked):
    """У кандидата нет `item_id` — он ещё не в базе, и сохранять обложку
    некуда."""
    answers, log = asked
    answers["posters.poster_for"] = JPEG

    status, headers, body = call(Page(spy, tmp_path), "/poster", CANDIDATE)

    assert status.startswith("200")
    assert headers["Content-Type"] == "image/jpeg"
    assert body == JPEG
    assert [name for name, _, _ in log] == ["posters.poster_for"]
    _, args, _ = log[0]
    assert args[0] is None
    assert args[1] is Source.TMDB


def test_a_cover_that_did_not_arrive_is_not_found(tmp_path, spy, asked):
    """Не приехала — на её месте заглушка, и делает её `onerror` у картинки, а
    не пустой ответ с кодом 200."""
    answers, _ = asked
    answers["posters.poster_for"] = None

    status, _, _ = call(Page(spy, tmp_path), "/poster", CANDIDATE)

    assert status.startswith("404")


def test_a_refused_source_does_not_pretend_to_be_a_picture(tmp_path, spy,
                                                           asked):
    """Отказ источника — не картинка: отдать его байтами значило бы нарисовать
    в карточке битый файл."""
    answers, _ = asked
    answers["posters.poster_for"] = Refusal(source="tmdb",
                                            reason=Reason.NETWORK)

    status, headers, _ = call(Page(spy, tmp_path), "/poster", CANDIDATE)

    assert status.startswith("404")
    # Сутки кеша на «не приехала» означали бы сутки пустого места при живой
    # сети: заглушку рисует `onerror`, и переспросить он должен сразу.
    assert "Cache-Control" not in headers


def test_a_thread_that_refused_gives_a_place_for_the_stub(tmp_path, spy, asked,
                                                          caplog):
    """Сюда сходятся три беды разом — закрытый поток, истёкший срок и сбой
    бэкенда. Отдавать в ответ исключение обработчик не вправе: это ответ
    браузеру, а не странице."""
    answers, _ = asked
    answers["posters.poster_for"] = RuntimeError("сеть отвалилась")

    status, _, _ = call(Page(spy, tmp_path), "/poster", CANDIDATE)

    assert status.startswith("404")
    assert "обложка не доехала" in caplog.text


def test_an_empty_picture_is_not_a_picture_either(tmp_path, spy, asked):
    """Пустые байты в хранилище неотличимы от их отсутствия — проект уже ловил
    это однажды; отдавать их как картинку нельзя."""
    answers, _ = asked
    answers["posters.poster_for"] = b""

    status, _, _ = call(Page(spy, tmp_path), "/poster", CANDIDATE)

    assert status.startswith("404")


def test_a_cover_of_a_card_that_is_gone_is_not_found(tmp_path, spy, asked):
    """Карточку удалили, пока лента её рисовала: обложке взяться неоткуда, а
    падать обработчику нельзя."""
    answers, log = asked
    answers["library.get"] = None

    status, _, _ = call(Page(spy, tmp_path), "/poster", "item=12")

    assert status.startswith("404")
    assert [name for name, _, _ in log] == ["library.get"]


def test_a_cover_asked_without_anything_is_refused(tmp_path, spy, asked):
    status, _, _ = call(Page(spy, tmp_path), "/poster")
    assert status.startswith("400")


def test_a_number_that_is_not_a_number_is_a_bad_request(tmp_path, spy, asked):
    """Нечисловой номер — поломка страницы, а не отсутствие обложки. Отдав на
    него 404, мы спрятали бы её за нормальным исходом, и до бэкенда он не
    доходит вовсе."""
    _, log = asked

    status, _, _ = call(Page(spy, tmp_path), "/poster", "item=абв")

    assert status.startswith("400")
    assert log == []


def test_a_page_file_that_will_not_read_is_not_found(tmp_path, spy, caplog):
    """Под заморозкой pywebview подменяет `stderr` на пустоту: непойманная
    ошибка чтения дала бы пустое окно без единой строки в логе."""
    (tmp_path / "index.html").mkdir()

    status, _, _ = call(Page(spy, tmp_path), "/index.html")

    assert status.startswith("404")
