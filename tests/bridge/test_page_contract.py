"""Имена, которые страница и мост обязаны называть одинаково.

Своей проверки у этих пар нет ни с одной стороны: питон не читает `client/`,
Vitest не читает `bridge/`. Ломаются они по-разному, и тише всех — фильтры:
раздел, тип и критерий сортировки мост переводит в перечисления и на неизвестном
падает `ValueError`, а фильтры читает через `filters.get(name, ())`, где
разъехавшееся имя даёт не отказ, а фильтр, который молча не применился.

Читается исходник страницы, а не собранный бандл: сборки может не быть вовсе, а
имена обязаны совпадать и до неё."""

import re
from dataclasses import fields
from pathlib import Path

from backend.model import (
    Rating,
    CompanyRole,
    IdSource,
    Kind,
    PersonRole,
    RatingSource,
    Section,
    Sort,
)
from bridge.feed import FILTER_FIELDS

WEB = Path(__file__).resolve().parents[2] / "client"

# Тело `chosen` — единственное место страницы, где имена фильтра пишутся.
CHOSEN = re.compile(r"export function chosen\(filters\) \{(.+?)\n\}", re.DOTALL)


def source(path: str) -> str:
    return (WEB / path).read_text(encoding="utf-8")


def named_in_chosen() -> set[str]:
    body = CHOSEN.search(source("state/filters.js"))
    assert body, "в client/state/filters.js больше нет функции chosen"
    return set(re.findall(r"^\s{4}(\w+):", body.group(1), re.MULTILINE))


def values_of(table: str, text: str) -> set[str]:
    """Значения `value:` внутри одной таблицы, до её закрывающей скобки."""
    start = text.index(f"const {table} = [")
    return set(re.findall(r"value: '(\w+)'", text[start:text.index("]", start)]))


def keys_of(table: str, text: str) -> set[str]:
    """Ключи словаря `const ИМЯ = { ... }`.

    Скобки считаются, а не ищутся первой закрывающей: `${...}` внутри шаблонной
    строки оборвал бы словарь на середине. Сами шаблоны выкидываются до разбора
    — иначе `https:` в адресе читается ключом."""
    opened = text.index("{", text.index(f"const {table} = {{"))
    depth, end = 0, len(text)
    for index in range(opened, len(text)):
        depth += {"{": 1, "}": -1}.get(text[index], 0)
        if not depth:
            end = index
            break
    return set(re.findall(r"[{,]\s*(\w+):",
                          re.sub(r"`[^`]*`", "''", text[opened:end])))


def test_the_page_names_exactly_what_the_bridge_reads():
    assert named_in_chosen() == set(FILTER_FIELDS)


def test_the_page_offers_exactly_the_kinds_the_backend_knows():
    """Переключатель типа — три кнопки, и каждая уезжает в `Kind`."""
    assert values_of("KINDS", source("app/Topbar.svelte")) == set(Kind)


def test_the_library_halves_match_the_sections_the_base_serves():
    """Поиска и статистики в `Section` нет намеренно: их база не отдаёт вовсе —
    поиск складывает две выдачи сам, статистика спрашивает гистограмму."""
    assert values_of("VIEWS", source("app/Topbar.svelte")) == set(Section)


def test_the_switch_offers_exactly_the_orders_the_base_supports():
    keys = set(re.findall(r"key: '?(\w+)'?,", source("state/sorting.js")))
    # `ADDED_AT` в таблице стоит именем константы, а не строкой.
    assert (keys - {"ADDED_AT"}) | {Sort.ADDED_AT} == set(Sort)


def test_every_rating_source_has_a_scale_and_a_name():
    """Оценки приезжают ключами `RatingSource`, а страница берёт по ним шкалу и
    подпись. Разъехавшись, они молчат вдвойне: неизвестная шкала уходит в
    запасную десятибалльную, неизвестное имя показывается сырым ключом."""
    page = source("state/sources.js")

    assert keys_of("MAX", page) == set(RatingSource)
    assert keys_of("NAMES", page) == set(RatingSource)


def test_pages_are_built_only_for_ids_that_are_actually_stored():
    """Адрес собирается по чужому идентификатору, а чужими сегодня приезжают
    только IMDb и Кинопоиск: `IdSource` знает ещё Steam и GOG, но их не пишет
    ни один клиент. Строка про источник, которого в перечислении нет вовсе, —
    это ссылка в никуда."""
    built = keys_of("PAGES", source("state/sources.js"))

    assert built <= set(IdSource)
    assert built == {IdSource.IMDB, IdSource.KINOPOISK}


def test_the_card_shows_every_role_the_base_stores():
    """Строки состава на карточке перечислены своей таблицей. Переименованная
    роль отказа не даёт — строка просто исчезает со всех карточек разом, а
    заметить это можно только глазами и только зная, что она там была."""
    card = source("components/Facts.svelte")
    named = set(re.findall(r"role: '(\w+)'", card))

    assert named == set(PersonRole) | set(CompanyRole)


def test_the_page_names_the_same_three_aspects_as_the_base():
    """Три стороны оценки игры уезжают мосту именами полей: `wire.py` кладёт
    датакласс на провод как есть. Переименованная сторона отказа не даёт —
    строка шкалы гаснет на всех играх молча, а среднее считается по двум."""
    named = set(re.findall(r"key: '(\w+)'", source("state/scores.js")))
    stored = {field.name for field in fields(Rating)} - {"item_id", "score",
                                                         "review"}

    assert named == stored


def test_the_card_asks_the_right_two_shelves():
    """Люди и студии лежат в разных репозиториях, и мост зовёт их по имени
    домена. Перепутанные местами, они дали бы режиссёра среди студий — ровно та
    ошибка, которую проект уже ловил мутациями в сборке бэкенда."""
    card = source("components/Facts.svelte")

    assert set(re.findall(r"from: '(\w+)'", card)) == {"people", "companies"}


def test_sorting_is_offered_exactly_where_the_base_can_sort():
    """Круг состояний заведён ровно тем разделам, которые база и сортирует.
    Разойдясь, они дали бы либо кнопку, которая ничего не меняет, либо раздел с
    порядком, но без переключателя."""
    cycles = re.search(r"const CYCLES = \{(.+?)\n\}", source("state/sorting.js"),
                       re.DOTALL)
    assert cycles, "в client/state/sorting.js больше нет таблицы CYCLES"
    assert set(re.findall(r"^\s{2}(\w+):", cycles.group(1),
                          re.MULTILINE)) == set(Section)
