"""Свой код проекта как дерево разбора.

Отсюда берут материал обе карты и вердикты: где лежат наши папки, какие в них
модули, что каждый объявляет и чем одно объявление отличается от другого.
Разметку не рисует и файлов не пишет — этим заняты соседи.

Корень ищется от текущей папки вверх до `.git`, а не от пути этого файла: он
живёт копией в проекте и образцом в скилле, и по своему пути нашёл бы репозиторий
скилла, а не разбираемый проект.
"""

import ast
from hashlib import sha1
from pathlib import Path

# Длина отпечатка: восьми шестнадцатеричных знаков хватает, чтобы отличить одно
# объявление проекта от другого, и они ещё читаются глазами в строке вердикта.
STAMP = 8

SKIP = {
    ".git", ".venv", "venv", "env", "__pycache__", "node_modules", "build",
    ".claude", ".pytest_cache", ".ruff_cache", ".mypy_cache", "docs",
}
DEFINITIONS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)


def project_root() -> Path:
    """Корень проекта: ближайшая папка с `.git` от текущей вверх."""
    here = Path.cwd().resolve()
    for folder in (here, *here.parents):
        if (folder / ".git").exists():
            return folder
    return here


ROOT = project_root()


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
        # Пропускаемое ищется в пути от корня проекта, а не в абсолютном: иначе
        # проект, лежащий внутри папки с таким именем, отбрасывает сам себя
        # целиком. Так и вышло с рабочими деревьями агентов внутри `.claude`:
        # карта там не собиралась вовсе.
        inside = [
            path
            for path in sorted((ROOT / root).rglob("*.py"))
            if not SKIP.intersection(path.relative_to(ROOT).parts)
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


def size(node: ast.AST) -> int:
    return (node.end_lineno or node.lineno) - node.lineno + 1


def _siblings(path: str) -> set[str]:
    """Модули рядом с этим, доступные ему по короткому имени.

    Плоский `import project_ast` — такая же зависимость, как `from backend...`,
    но по первому слову её не узнать: слово не совпадает ни с одной папкой
    верхнего уровня. Не разобрав её, карта пишет «зависит от: —» тому, кто
    зависит от двух соседей."""
    folder = ROOT / path
    return {one.stem for one in folder.parent.glob("*.py") if one.name != folder.name}


def depends_on(tree: ast.Module, path: str = "") -> list[str]:
    """Модули проекта, от которых зависит этот. Чужие библиотеки не в счёт."""
    near = _siblings(path) if path else set()
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split(".")[0] in roots() or node.module in near:
                found.add(node.module)
        elif isinstance(node, ast.Import):
            for imported in node.names:
                if imported.name.split(".")[0] in roots() or imported.name in near:
                    found.add(imported.name)
    return sorted(found)


def exported(tree: ast.Module) -> list[str]:
    """Имена из `__all__`: у пакета это и есть его поверхность наружу."""
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        ):
            return list(ast.literal_eval(node.value))
    return []


def implementations(found: list[tuple]) -> dict[str, list[str]]:
    """Базовый класс -> кто его наследует. Пусто у того, кого не наследуют.

    Чужие основания не в счёт: `Exception` с единственным наследником — не
    заведённая нами абстракция, а обычное своё исключение, и правило 7 про
    него ничего не говорит."""
    children: dict[str, list[str]] = {}
    ours: set[str] = set()
    for _path, tree, _lines in found:
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            ours.add(node.name)
            children.setdefault(node.name, [])
            for base in node.bases:
                children.setdefault(ast.unparse(base), []).append(node.name)
    return {base: kids for base, kids in children.items() if base in ours}


def bound_names(node: ast.AST) -> list[str]:
    """Имена, которые связывает присваивание. Не присваивание — пусто.

    Слева бывает несколько: `A = B = 1` и `A, B = 1, 2` — это два объявления, и
    потерять второе значит сказать, что его нет."""
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return [node.target.id]
    if not isinstance(node, ast.Assign):
        return []
    names: list[str] = []
    for target in node.targets:
        parts = target.elts if isinstance(target, ast.Tuple | ast.List) else [target]
        names += [part.id for part in parts if isinstance(part, ast.Name)]
    return names


def _stamp(node: ast.AST | None) -> str:
    return sha1(ast.dump(node).encode("utf-8")).hexdigest()[:STAMP] if node else ""


def declarations(found: list[tuple]) -> dict[str, str]:
    """Всё, на что можно сослаться именем, и отпечаток этого.

    Ключ — `путь:Класс.имя`, по нему на объявление ссылается файл вердиктов.
    Кроме функций и классов сюда идут константы, поля и значения перечислений:
    повторяются они не реже, а карта данных ровно их и показывает.

    Отпечаток берётся с узла целиком, вместе с сигнатурой: сменившийся тип
    аргумента меняет дело так же, как переписанное тело."""
    index: dict[str, str] = {}

    def walk(body: list, path: str, prefix: str) -> None:
        for node in body:
            for name in bound_names(node):
                index[f"{path}:{prefix}{name}"] = _stamp(node.value)
            if not isinstance(node, DEFINITIONS):
                continue
            name = f"{prefix}{node.name}"
            index[f"{path}:{name}"] = _stamp(node)
            walk(node.body, path, f"{name}.")

    for path, tree, _lines in found:
        walk(tree.body, path, "")
    return index
