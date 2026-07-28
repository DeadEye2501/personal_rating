"""Карта модулей: кто за что отвечает, что объявляет и от кого зависит.

Нужна там, где правила манифеста не проверить по одному диффу: «ищи готовое»,
«место выбирается до первой строки», «одна ответственность на модуль»,
«абстракция появляется со второй реализацией». Рецензент читает карту вместо
всего кода, и цена проверки перестаёт зависеть от размера проекта.

Карта собирается из кода, а не ведётся руками: забыть дописать функцию нельзя.

    pipenv run python scripts/module_map.py           пересобрать docs/module-map.md
    pipenv run python scripts/module_map.py --check   упасть, если карта устарела
"""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "docs/module-map.md"
PACKAGES = ("backend", "client")
SKIP = {"__pycache__"}
DEFINITIONS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def modules() -> list[tuple[str, ast.Module, int]]:
    """Модули проекта: путь от корня, разобранное дерево и число строк.

    `__init__.py` не пропускается: в `backend/model` он и есть та поверхность,
    которую клиенту разрешено импортировать, — спрятать её значило бы соврать."""
    found = []
    for package in PACKAGES:
        # Пустой ответ — поломка карты, а не чистый пакет: и отсутствующая
        # папка, и сломанная маска отдают пустоту, а не исключение.
        assert (ROOT / package).is_dir(), f"нет пакета {package}"
        inside = [
            path
            for path in sorted((ROOT / package).rglob("*.py"))
            if not SKIP.intersection(path.parts)
        ]
        assert inside, f"в пакете {package} не найдено ни одного файла"
        for path in inside:
            text = path.read_text(encoding="utf-8")
            tree = ast.parse(text)
            # Пустой `__init__.py` — маркер пакета, называть в нём нечего.
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


def size(node: ast.AST) -> int:
    return (node.end_lineno or node.lineno) - node.lineno + 1


def depends_on(tree: ast.Module) -> list[str]:
    """Модули проекта, от которых зависит этот. Чужие библиотеки не в счёт."""
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split(".")[0] in PACKAGES:
                found.add(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in PACKAGES:
                    found.add(alias.name)
    return sorted(found)


def members(node: ast.ClassDef) -> list[str]:
    """Методы и свойства класса. Поля датакласса не в счёт: они в спеке."""
    return [
        f"  - `{signature(child)}` ({size(child)})"
        for child in node.body
        if isinstance(child, DEFINITIONS) and not child.name.startswith("_")
    ]


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
    said = doc.split("\n")[0].strip() if doc else "**ответственность не названа**"
    uses = ", ".join(f"`{one}`" for one in depends_on(tree)) or "—"
    warn = " ⚠ за пределом 500" if lines_total > 500 else (
        " ⚠ подошёл к 300" if lines_total > 300 else ""
    )
    lines = [f"### `{path}` — {lines_total} строк{warn}", "", said, "",
             f"Зависит от: {uses}", ""]
    names = exported(tree)
    if names:
        lines += [f"Отдаёт наружу: {', '.join(f'`{one}`' for one in names)}", ""]
    for node in tree.body:
        if not isinstance(node, DEFINITIONS):
            continue
        lines.append(f"- `{signature(node)}` ({size(node)})")
        if isinstance(node, ast.ClassDef):
            lines += members(node)
    return "\n".join([*lines, ""])


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


def render() -> str:
    found = modules()
    parts = [
        "# Карта модулей",
        "",
        "Собирается из кода: `pipenv run python scripts/module_map.py`.",
        "Править руками нельзя — правки затрёт следующая сборка.",
        "Число в скобках — сколько строк занимает объявление.",
        "",
    ]
    for package in PACKAGES:
        inside = [one for one in found if one[0].startswith(package)]
        parts.append(f"## {package} — {len(inside)} модулей\n")
        parts += [module_block(*one) for one in inside]
    parts.append(lonely_block(found))
    return "\n".join(parts)


def main() -> int:
    fresh = render()
    if "--check" in sys.argv:
        stored = MAP.read_text(encoding="utf-8") if MAP.exists() else ""
        if stored == fresh:
            print("карта свежая")
            return 0
        print("карта устарела: пересобери pipenv run python scripts/module_map.py")
        return 1
    MAP.write_text(fresh, encoding="utf-8")
    print(f"карта пересобрана: {len(modules())} модулей")
    return 0


if __name__ == "__main__":
    sys.exit(main())
