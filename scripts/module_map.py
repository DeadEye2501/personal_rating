"""Две карты проекта, собираемые из кода.

Нужны там, где правила манифеста не проверить по одному диффу: «ищи готовое»,
«место выбирается до первой строки», «одна ответственность на модуль»,
«абстракция появляется со второй реализацией». Рецензент читает карты вместо
всего кода, и цена проверки перестаёт зависеть от размера проекта.

Карт две, потому что повторяется двоякое. `module-map.md` — кто за что отвечает,
что объявляет и от кого зависит: там видно вторую функцию с тем же делом.
`data-map.md` — из чего объявленное состоит: поля классов, значения перечислений,
таблицы и константы. Там видно второе перечисление с теми же значениями и вторую
таблицу под другим именем — из карты модулей они выглядят как разные классы.

Карты собираются из кода, а не ведутся руками: забыть дописать функцию нельзя.

Охват — весь свой код, а не только боевой: тесты, скрипты и миграции пишем мы
же, и повторы там заводятся ровно так же. Из тестов в карты идут помощники,
фикстуры и константы, а сами тесты только считаются: их имена говорят сами за
себя, а общее прячется не в них.

    python <путь до этого файла>           пересобрать обе карты и заверить вердикты
    python <путь до этого файла> --check   упасть, если карта устарела или вердикт протух

Файл рядом с соседями `project_ast.py` и `not_duplicates.py`; все три в проекте
и в скилле совпадают побайтно.
"""

import ast
import sys
from pathlib import Path

import not_duplicates
from project_ast import (
    DEFINITIONS,
    FUNCTIONS,
    ROOT,
    bound_names,
    declarations,
    depends_on,
    exported,
    implementations,
    modules,
    roots,
    signature,
    size,
)

MAP = ROOT / "docs/module-map.md"
DATA_MAP = ROOT / "docs/data-map.md"
# Длинное значение в карту не переносится: важно, что таблица есть и какова
# она размером, а не что в ней.
SHORT_VALUE = 48


def alias(node: ast.AST) -> str | None:
    """Псевдоним типа, если это он. Такое же имя поверхности, как класс: его
    импортируют и им аннотируют. Прочие присваивания в карту модулей не идут —
    констант в модуле десятки, а имён типов единицы.

    Форм две. В этом проекте встречается только `X: TypeAlias = ...`, но файл
    переносится в чужие, где с Python 3.12 обычнее `type X = ...`; разбирать
    одну и слепнуть ко второй значит соврать в карте молча."""
    if isinstance(node, ast.TypeAlias):
        return f"type {ast.unparse(node.name)} = {ast.unparse(node.value)}"
    named = (
        isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and ast.unparse(node.annotation) == "TypeAlias"
        and node.value is not None
    )
    return f"{node.target.id}: TypeAlias = {ast.unparse(node.value)}" if named else None


def declared(body: list, depth: int = 0) -> tuple[list[str], int]:
    """Объявления тела и число тестов в нём.

    Показывается всё, до чего можно дотянуться именем: приватные методы,
    вложенные функции, классы. Общее выносят как раз в приватные помощники, а
    фикстуры возвращают замыкания — спрятав их, карта слепнет ровно к тому,
    ради чего её и завели.

    Не показываются двое. `__init__` есть у всех и ничего не говорит. Тесты
    только считаются: их имя и есть их описание, а повтор прячется не в них, а
    в помощниках рядом."""
    lines: list[str] = []
    tests = 0
    for node in body:
        named = alias(node)
        if named:
            lines.append(f"{'  ' * depth}- `{named}`")
            continue
        if not isinstance(node, DEFINITIONS):
            continue
        if isinstance(node, FUNCTIONS) and node.name.startswith("test_"):
            tests += 1
            continue
        if node.name == "__init__":
            continue
        lines.append(f"{'  ' * depth}- `{signature(node)}` ({size(node)})")
        inside, counted = declared(node.body, depth + 1)
        lines += inside
        tests += counted
    return lines, tests


def module_block(path: str, tree: ast.Module, lines_total: int) -> str:
    doc = ast.get_docstring(tree)
    # У файла с тестами ответственность названа его именем, и требовать от него
    # докстринг значит разводить шум. У остальных безымянная ответственность —
    # это и есть находка: правило 6 иначе не проверить.
    unnamed = (
        "" if Path(path).name.startswith("test_")
        else "**ответственность не названа**"
    )
    said = doc.split("\n")[0].strip() if doc else unnamed
    uses = ", ".join(f"`{one}`" for one in depends_on(tree, path)) or "—"
    warn = " ⚠ за пределом 500" if lines_total > 500 else (
        " ⚠ подошёл к 300" if lines_total > 300 else ""
    )
    lines = [f"### `{path}` — {lines_total} строк{warn}", "", said, "",
             f"Зависит от: {uses}", ""]
    names = exported(tree)
    if names:
        lines += [f"Отдаёт наружу: {', '.join(f'`{one}`' for one in names)}", ""]
    inside, tests = declared(tree.body)
    if tests:
        lines += [f"Тестов: {tests}", ""]
    lines += inside
    return "\n".join([*lines, ""])


def _counted(kind: str, amount: int, spread: bool) -> str:
    """Подпись размера. Имя не `size`: у соседа так зовётся число строк узла, и
    два разных дела под одним словом читаются как одно."""
    return f"{kind} из {amount} и раскрытых" if spread else f"{kind} из {amount}"


def brief(value: ast.AST | None) -> str:
    """Значение коротко. У набора называется размер, а не содержимое: два
    справочника тегов различаются тем, что их два, а не тем, что внутри.

    Раскрытое внутри не пересчитывается: `{**BASE, "x": 1}` знает про свой один
    ключ и не знает, сколько их в `BASE`. Поэтому размер называется с оговоркой,
    а не выдаётся за точный."""
    if value is None:
        return ""
    if isinstance(value, ast.Dict):
        spread = value.keys.count(None)
        return _counted("словарь", len(value.keys) - spread, bool(spread))
    if isinstance(value, ast.Set | ast.List | ast.Tuple):
        spread = sum(isinstance(item, ast.Starred) for item in value.elts)
        return _counted("набор", len(value.elts) - spread, bool(spread))
    text = ast.unparse(value)
    return text if len(text) <= SHORT_VALUE else f"{text[:SHORT_VALUE]}…"


def assigned(node: ast.AST) -> list[tuple[str, str]]:
    """Присваивания узла парами «имя, значение коротко». Не присваивание — пусто.

    Поля датакласса, значения перечисления, таблицы и константы объявляются
    одинаково, поэтому разбирает их одно место. Слева бывает несколько имён:
    `A = B = 1` и `A, B = 1, 2` — это два объявления, и потерять второе значит
    сказать в карте, что его нет."""
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return [(f"{node.target.id}: {ast.unparse(node.annotation)}",
                 brief(node.value))]
    return [(name, brief(node.value)) for name in bound_names(node)]


def _data_nodes(body: list) -> list[ast.AST]:
    """Тело вместе с тем, что спрятано в `if` и `try`: константа под
    `if TYPE_CHECKING:` — такая же константа, а её отсутствие в карте читается
    как «данных нет», а не как «мы туда не заглянули»."""
    found: list[ast.AST] = []
    for node in body:
        if isinstance(node, ast.If | ast.Try):
            found += _data_nodes(node.body) + _data_nodes(node.orelse)
        else:
            found.append(node)
    return found


def _class_lines(node: ast.ClassDef) -> list[str]:
    """Класс с полями и вложенными классами. Класс без полей ничего не даёт:
    его имя уже названо картой модулей."""
    lines: list[str] = []
    for item in _data_nodes(node.body):
        if isinstance(item, ast.ClassDef):
            lines += [f"  {line}" for line in _class_lines(item)]
        else:
            lines += [f"  - `{name}`" + (f" = `{value}`" if value else "")
                      for name, value in assigned(item)]
    return [f"- `{signature(node)}`", *lines] if lines else []


def contents(tree: ast.Module) -> list[str]:
    """Данные модуля: поля классов, значения перечислений, таблицы, константы.

    Карта модулей показывает оболочки — `class Item` и `class Reason`, — а из
    чего они состоят, не показывает. Между тем повторяются как раз наборы: два
    перечисления с одними значениями или вторая таблица под другим именем видны
    только отсюда.

    Имя регистром не отбирается. Проверено потерей: под `isupper()` из карты
    выпали все четырнадцать таблиц схемы — они объявлены строчными, — то есть
    ровно тот случай, ради которого карта и заведена."""
    lines: list[str] = []
    for node in _data_nodes(tree.body):
        if isinstance(node, ast.ClassDef):
            lines += _class_lines(node)
        else:
            # `__all__` целиком печатает карта модулей, повторять её незачем.
            lines += [f"- `{name}` = `{value}`"
                      for name, value in assigned(node) if name != "__all__"]
    return lines


def data_block(path: str, tree: ast.Module) -> list[str]:
    """Раздел карты данных про один модуль. Модуль без данных не даёт ничего."""
    lines = contents(tree)
    return [f"### `{path}`", "", *lines, ""] if lines else []


def lonely_block(found: list[tuple]) -> str:
    """Правило 7: абстракция заводится со второй реализацией, не раньше."""
    lonely = [
        f"- `{base}` — наследник один: `{kids[0]}`"
        for base, kids in sorted(implementations(found).items())
        if len(kids) == 1
    ]
    body = "\n".join(lonely) if lonely else "Нет."
    return f"## Абстракции с одной реализацией\n\n{body}\n"


def within(found: list[tuple], root: str) -> list[tuple]:
    """Модули одной папки верхнего уровня. Сравнивается первая часть пути, а не
    его начало: иначе папка `test` забрала бы себе модули из `tests`."""
    return [one for one in found if one[0].split("/")[0] == root]


def heading(title: str, note: str) -> list[str]:
    return [f"# {title}", "",
            "Собирается из кода, а не ведётся руками.",
            "Править руками нельзя — правки затрёт следующая сборка.",
            note, ""]


def render(found: list[tuple]) -> str:
    parts = heading("Карта модулей",
                    "Число в скобках — сколько строк занимает объявление.")
    for root in roots():
        inside = within(found, root)
        parts.append(f"## {root} — {len(inside)} модулей\n")
        parts += [module_block(*one) for one in inside]
    parts.append(lonely_block(found))
    return "\n".join(parts)


def render_data(found: list[tuple]) -> str:
    """Карта данных: то, из чего состоят объявления карты модулей."""
    parts = heading("Карта данных", "У набора называется размер, а не содержимое.")
    for root in roots():
        blocks: list[str] = []
        for path, tree, _lines in within(found, root):
            blocks += data_block(path, tree)
        if blocks:
            parts.append(f"## {root}\n")
            parts.append("\n".join(blocks))
    return "\n".join(parts)


def main() -> int:
    found = modules()
    maps = ((MAP, render(found)), (DATA_MAP, render_data(found)))
    index = declarations(found)
    if "--check" not in sys.argv:
        for path, fresh in maps:
            path.write_text(fresh, encoding="utf-8")
        not_duplicates.seal(index)
        print(f"карты пересобраны: {len(found)} модулей")
        return 0

    stale = [path.name for path, fresh in maps
             if (path.read_text(encoding="utf-8") if path.exists() else "") != fresh]
    if stale:
        print(f"устарело: {', '.join(stale)} — "
              f"пересобери python {Path(sys.argv[0]).as_posix()}")
        return 1
    gone = not_duplicates.expired(not_duplicates.verdict_lines(), index)
    if gone:
        print("вердикты протухли, пары вернулись в разбор:\n  " + "\n  ".join(gone))
        return 1
    print("карты свежие, вердикты в силе")
    return 0


if __name__ == "__main__":
    sys.exit(main())
