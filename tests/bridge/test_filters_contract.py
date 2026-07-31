"""Шесть имён фильтра совпадают у страницы и у моста.

Своей проверки у этой пары нет ни с одной стороны: питон не читает `client/`,
Vitest не читает `bridge/`. А ломается она тише всех остальных контрактов
границы — раздел и критерий сортировки мост переводит в перечисления и на
неизвестном падает `ValueError`, фильтры же он читает через
`filters.get(name, ())`, и разъехавшееся имя даёт не отказ, а фильтр, который
молча не применился."""

import re
from pathlib import Path

from bridge.feed import FILTER_FIELDS

CHOSEN = Path(__file__).resolve().parents[2] / "client" / "state" / "filters.js"

# Тело `chosen` — единственное место страницы, где эти имена пишутся.
BODY = re.compile(r"export function chosen\(filters\) \{(.+?)\n\}", re.DOTALL)


def named() -> set[str]:
    body = BODY.search(CHOSEN.read_text(encoding="utf-8"))
    assert body, "в client/state/filters.js больше нет функции chosen"
    return set(re.findall(r"^\s{4}(\w+):", body.group(1), re.MULTILINE))


def test_the_page_names_exactly_what_the_bridge_reads():
    assert named() == set(FILTER_FIELDS)
