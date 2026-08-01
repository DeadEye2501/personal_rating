"""Имена, которые страница и мост обязаны называть одинаково.

Своей проверки у этих пар нет ни с одной стороны: питон не читает `client/`,
Vitest не читает `bridge/`. Ломаются они по-разному, и тише всех — фильтры:
раздел, тип и критерий сортировки мост переводит в перечисления и на неизвестном
падает `ValueError`, а фильтры читает через `filters.get(name, ())`, где
разъехавшееся имя даёт не отказ, а фильтр, который молча не применился.

Читается исходник страницы, а не собранный бандл: сборки может не быть вовсе, а
имена обязаны совпадать и до неё."""

import re
from pathlib import Path

from backend.model import Kind, Section, Sort
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


def test_sorting_is_offered_exactly_where_the_base_can_sort():
    """Круг состояний заведён ровно тем разделам, которые база и сортирует.
    Разойдясь, они дали бы либо кнопку, которая ничего не меняет, либо раздел с
    порядком, но без переключателя."""
    cycles = re.search(r"const CYCLES = \{(.+?)\n\}", source("state/sorting.js"),
                       re.DOTALL)
    assert cycles, "в client/state/sorting.js больше нет таблицы CYCLES"
    assert set(re.findall(r"^\s{2}(\w+):", cycles.group(1),
                          re.MULTILINE)) == set(Section)
