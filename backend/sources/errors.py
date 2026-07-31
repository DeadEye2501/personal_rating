"""Как источник сообщает, что ответ не разобрался."""

from collections.abc import Callable
from logging import Logger

import httpx

from backend.model import Missing, Reason, Refusal

# Чем падает разбор чужого ответа. Не только `ValueError`: на словаре вместо
# списка приезжает `TypeError`, на отсутствующем ключе — `KeyError`, на `None`
# вместо тела — `AttributeError`.
BROKEN_BY_PARSING = (ValueError, TypeError, KeyError, AttributeError)


def broken(source: str, error: Exception) -> Refusal:
    """Отказ по неразобранному ответу. Запись в лог остаётся на месте вызова:
    сообщение у каждого своё, и по нему потом ищут причину."""
    return Refusal(source=source, reason=Reason.BROKEN, detail=str(error))


def absent(response: httpx.Response, source: str) -> Missing | Refusal:
    """«Такого у меня нет» — только по разобранному телу.

    Перед двумя источниками стоит чужой периметр: перед Кинопоиском Envoy, перед
    MDBList Cloudflare, — и своя страница под 404 приезжает у них текстом.
    Записать её как ответ значит поселить в базе ложь на неделю, а у MDBList
    сразу в четырёх источниках: пустое пишется по всему `PROVIDES`.

    Отказ здесь `BROKEN`, а не `NETWORK`: чей это 404 — периметра или самого
    источника — по телу не видно, и в обоих случаях это ответ, которому нельзя
    верить."""
    if not is_json(response):
        return Refusal(source=source, reason=Reason.BROKEN,
                       detail="404 без JSON — это не «такого нет»")
    return Missing()


def refuse_code(source: str, status: int) -> Refusal:
    """Код, которого у источника не описано. Была функцией у зеркал Кинопоиска и
    держала их `SOURCE` внутри, поэтому остальные трое ею воспользоваться не
    могли и писали то же выражение по месту."""
    return Refusal(source=source, reason=Reason.BROKEN, detail=f"HTTP {status}")


def is_json(response: httpx.Response) -> bool:
    """Разобралось ли тело — не ради тела, а ради решения, верить ли коду.

    Приём один у двоих: перед Кинопоиском стоит Envoy и отдаёт свой 404 текстом,
    перед MDBList — Cloudflare со своим 403. Отсюда два разных вывода, и оба
    стоят на этой проверке: `absent` не верит коду «такого нет», а `_denied` у
    MDBList отличает чужой периметр от битого ключа."""
    try:
        response.json()
    except ValueError:
        return False
    return True


def parsed[T](log: Logger, source: str, note: str,
              produce: Callable[[], T]) -> T | Refusal:
    """Разбор чужого ответа: получилось — отдаём как есть, сорвалось — записываем
    и отказываем.

    Заведено на девяти копиях одного и того же `try/except` в шести клиентах:
    седьмой источник, написанный по образцу, легко получил бы `except Exception`
    вместо перечня или `Refusal` вместо `broken`, и заметить это было бы негде.

    `log` передаётся, а не берётся здесь: запись должна называть модуль
    источника, иначе в логе шесть клиентов выглядят одним. `note` — готовая
    фраза, а не подстановка: у клиента таких мест до трёх, и различает их только
    она."""
    try:
        return produce()
    except BROKEN_BY_PARSING as error:
        log.warning("%s: %s — %s", source, note, error)
        return broken(source, error)
