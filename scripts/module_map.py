"""Карты проекта, собираемые из кода.

Нужны там, где правила манифеста не проверить по одному диффу: «ищи готовое»,
«место выбирается до первой строки», «одна ответственность на модуль»,
«абстракция появляется со второй реализацией». Рецензент читает карты вместо
всего кода, и цена проверки перестаёт зависеть от размера проекта.

Карт две, потому что повторяется двоякое. `module-map.md` — кто за что отвечает,
что объявляет и от кого зависит: там видно вторую функцию с тем же делом.
`data-map.md` — из чего объявленное состоит: поля классов, значения перечислений
и константы модулей. Там видно второе перечисление с теми же значениями и вторую
таблицу под другим именем — из карты модулей они выглядят как разные классы.

Карты собираются из кода, а не ведутся руками: забыть дописать функцию нельзя.

Охват — весь свой код, а не только боевой: тесты, скрипты и миграции пишем мы
же, и повторы там заводятся ровно так же. Из тестов в карты идут помощники,
фикстуры и константы, а сами тесты только считаются: их имена говорят сами за
себя, а общее прячется не в них.

    python <путь до этого файла>           пересобрать обе карты
    python <путь до этого файла> --check   упасть, если карта устарела

Файл один на все проекты: копия в проекте и образец в скилле совпадают
побайтно. Корень ищется сам — от текущей папки вверх до `.git`, — и своего пути в карту
не пишет: иначе её содержимое зависело бы от того, как её запустили, и
`--check` расходился бы на ровном месте.
"""

import ast
import sys
from pathlib import Path


def project_root() -> Path:
    """Корень проекта: ближайшая папка с `.git` от текущей вверх.

    Считается от того, где стоишь, а не от того, где лежит файл: тот же файл
    живёт копией в проекте и образцом в скилле, и по его пути нашёлся бы
    репозиторий скилла, а не разбираемый проект."""
    here = Path.cwd().resolve()
    for folder in (here, *here.parents):
        if (folder / ".git").exists():
            return folder
    return here


ROOT = project_root()
MAP = ROOT / "docs/module-map.md"
DATA_MAP = ROOT / "docs/data-map.md"
# Длинное значение в карту не переносится: важно, что таблица есть и какова
# она размером, а не что в ней.
SHORT_VALUE = 48
SKIP = {
    ".git", ".venv", "venv", "env", "__pycache__", "node_modules", "build",
    ".claude", ".pytest_cache", ".ruff_cache", ".mypy_cache", "docs",
}
DEFINITIONS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)


def roots() -> list[str]:
    """Папки верхнего уровня, в которых лежит наш код."""
    found = sorted(
        path.name
        for path in ROOT.iterdir()
        if path.is_dir() and path.name not in SKIP and any(path.rglob("*.py"))
    )
    # Пустой ответ — поломка карты, а не проект без кода.
    assert found, f"в {ROOT} не найдено ни одной папки с кодом"
    return found


def modules() -> list[tuple[str, ast.Module, int]]:
    """Модули проекта: путь от корня, разобранное дерево и число строк.

    `__init__.py` не пропускается: у пакета с реэкспортом он и есть поверхность
    наружу, и спрятать её значило бы соврать. Пустой пропускается: маркер
    пакета называть нечем."""
    found = []
    for root in roots():
        inside = [
            path
            for path in sorted((ROOT / root).rglob("*.py"))
            if not SKIP.intersection(path.parts)
        ]
        assert inside, f"в {root} не найдено ни одного файла"
        for path in inside:
            text = path.read_text(encoding="utf-8")
            tree = ast.parse(text)
            if path.name == "__init__.py" and not tree.body:
                continue
            here = path.relative_to(ROOT).as_posix()
            found.append((here, tree, len(text.splitlines())))
    return found


def signature(node: ast.AST) -> str:
    if isinstance(node, ast.ClassDef):
        bases = ", ".join(ast.unparse(base) for base in node.bases)
        return f"class {node.name}({bases})" if bases else f"class {node.name}"
    kind = "async def " if isinstance(node, ast.AsyncFunctionDef) else "def "
    result = f" -> {ast.unparse(node.returns)}" if node.returns else ""
    return f"{kind}{node.name}({ast.unparse(node.args)}){result}"


def alias(node: ast.AST) -> str | None:
    """Псевдоним типа, если это он. Такое же имя поверхности, как класс: его
    импортируют и им аннотируют. Прочие присваивания в карту не идут — констант
    в модуле десятки, а имён типов единицы."""
    if isinstance(node, ast.TypeAlias):
        return f"type {ast.unparse(node.name)} = {ast.unparse(node.value)}"
    named = (
        isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and ast.unparse(node.annotation) == "TypeAlias"
        and node.value is not None
    )
    return f"{node.target.id}: TypeAlias = {ast.unparse(node.value)}" if named else None


def size(node: ast.AST) -> int:
    return (node.end_lineno or node.lineno) - node.lineno + 1


def depends_on(tree: ast.Module) -> list[str]:
    """Модули проекта, от которых зависит этот. Чужие библиотеки не в счёт."""
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split(".")[0] in roots():
                found.add(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in roots():
                    found.add(alias.name)
    return sorted(found)


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


def exported(tree: ast.Module) -> list[str]:
    """Имена из `__all__`: у пакета это и есть его поверхность наружу."""
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        ):
            return list(ast.literal_eval(node.value))
    return []


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
    uses = ", ".join(f"`{one}`" for one in depends_on(tree)) or "—"
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


def _size(kind: str, counted: int, spread: bool) -> str:
    return f"{kind} из {counted} и раскрытых" if spread else f"{kind} из {counted}"


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
        return _size("словарь", len(value.keys) - spread, bool(spread))
    if isinstance(value, ast.Set | ast.List | ast.Tuple):
        spread = sum(isinstance(item, ast.Starred) for item in value.elts)
        return _size("набор", len(value.elts) - spread, bool(spread))
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
    if not isinstance(node, ast.Assign):
        return []
    named: list[str] = []
    for target in node.targets:
        parts = target.elts if isinstance(target, ast.Tuple | ast.List) else [target]
        named += [part.id for part in parts if isinstance(part, ast.Name)]
    return [(name, brief(node.value)) for name in named]


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


def implementations(found: list[tuple]) -> dict[str, list[str]]:
    """Базовый класс -> кто его наследует. Пусто у того, кого не наследуют.

    Чужие основания не в счёт: `Exception` с единственным наследником — не
    заведённая нами абстракция, а обычное своё исключение, и правило 7 про
    него ничего не говорит."""
    children: dict[str, list[str]] = {}
    ours: set[str] = set()
    for _, tree, _lines in found:
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            ours.add(node.name)
            children.setdefault(node.name, [])
            for base in node.bases:
                children.setdefault(ast.unparse(base), []).append(node.name)
    return {base: kids for base, kids in children.items() if base in ours}


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
    if "--check" in sys.argv:
        stale = [path.name for path, fresh in maps
                 if (path.read_text(encoding="utf-8") if path.exists() else "") != fresh]
        if not stale:
            print("карты свежие")
            return 0
        print(f"устарело: {', '.join(stale)} — "
              f"пересобери python {Path(sys.argv[0]).as_posix()}")
        return 1
    for path, fresh in maps:
        path.write_text(fresh, encoding="utf-8")
    print(f"карты пересобраны: {len(found)} модулей")
    return 0


if __name__ == "__main__":
    sys.exit(main())
