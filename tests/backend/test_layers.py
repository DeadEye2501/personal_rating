"""Граница слоёв: кто кого имеет право импортировать.

Сторожит здесь только половина про бэкенд — та, у которой есть предмет: файлов в
нём полторы сотни. Второй половины, про сторону интерфейса, тут нет вовсе, и это
не дыра, а состояние проекта на 31.07.2026: питона на той стороне пока не
написано ни строки.

Раскладка при этом решена: `client/` — только фронт, ни одного `.py`; питон
стыка живёт в `bridge/`. Проверки «`bridge` не знает про базу и сеть» и
«`bridge` берёт из бэкенда только типы границы» заводятся вместе с первым файлом
`bridge/` — план 5, задача 2. Заводить их раньше нечем: `python_files`
утверждает, что пустой пакет это поломка проверки, а не чистый код, и оставленная
впрок проверка падала бы каждым прогоном.

Границу слоёв внутри `client/` этот файл не сторожит и не будет: там нет питона,
а слои держит хук на записи файла — `<style>` в компоненте, стиль вне `styles/`,
импорт вверх, цвет мимо палитры."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Договорённость двусторонняя: сторона интерфейса не знает про базу и сеть,
# бэкенд не знает про окно. Без второй половины `import webview` в бэкенде
# прошёл бы молча, а граница слоёв — это граница потоков: окно живёт в своём, и
# звать его оттуда, где работает бэкенд, нельзя.
#
# Имена — нынешнего стека: `webview` поднимает окно, `pythonnet` с `clr` тянутся
# за ним на Windows ради WinForms. Список обновлён вместе со сменой стека
# 31.07.2026: до неё здесь стоял снятый из проекта `PySide6`, и сторож
# сторожил отсутствующее.
BANNED_IN_BACKEND = {"bridge", "webview", "pythonnet", "clr"}


def imported_modules(path: Path):
    """Полные имена всех модулей, которые импортирует файл."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        # level > 0 — относительный импорт, он внутри своего же пакета
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module


def imported_roots(path: Path):
    """Только корневые имена: `sqlalchemy` из `sqlalchemy.ext.asyncio`."""
    for module in imported_modules(path):
        yield module.split(".")[0]


def python_files(package: str) -> list[Path]:
    """Файлы пакета. Пустой ответ — это поломка проверки, а не чистый пакет:
    и отсутствующая папка, и сломанная маска отдают пустоту, а не исключение."""
    assert (ROOT / package).is_dir(), f"нет пакета {package}"
    found = sorted((ROOT / package).rglob("*.py"))
    assert found, f"в пакете {package} не найдено ни одного файла"
    return found


def offenders(package: str, banned: set[str]) -> list[str]:
    found = []
    for path in python_files(package):
        for root in imported_roots(path):
            if root in banned:
                found.append(f"{path.relative_to(ROOT)} → {root}")
    return found


def test_backend_does_not_import_the_bridge_or_the_window():
    assert offenders("backend", BANNED_IN_BACKEND) == []


def test_the_model_depends_on_nothing_of_ours():
    """Модель — самый нижний слой, и на этом стоит переезд типов исхода в
    `backend/model/outcome.py`: стороне интерфейса открыта только она, значит она
    не вправе тянуть за собой ни хранилище, ни источники, ни сервисы.

    Раньше довод держался на одном докстринге. Импортируй `model/link.py`
    что-нибудь из `sources/` ради регулярок адресов — и тот, кто взял
    `parse_link`, получил бы вместе с ним `httpx`. Проверка выше этого не видит:
    она смотрит на импорты бэкенда наружу, а не внутрь модели."""
    found = []
    for path in python_files("backend/model"):
        for module in imported_modules(path):
            if not module.startswith("backend"):
                continue
            if module == "backend.model" or module.startswith("backend.model."):
                continue
            found.append(f"{path.relative_to(ROOT)} → {module}")

    assert found == []
