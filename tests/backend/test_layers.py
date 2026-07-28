import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

BANNED_IN_CLIENT = {"sqlalchemy", "aiosqlite", "httpx", "alembic", "PIL"}

# Договорённость двусторонняя: клиент не знает про базу и сеть, бэкенд не знает
# про Qt. Без второй половины `import PySide6` в бэкенде прошёл бы молча, а
# граница слоёв — это граница потоков, и виджет из чужого потока роняет окно.
BANNED_IN_BACKEND = {"client", "PySide6"}

# Из бэкенда клиенту открыты только типы границы и настройки. Всё прочее —
# репозитории, сервисы, клиенты источников — тянет за собой и сессию
# SQLAlchemy, и поход к диску в главном потоке, то есть ровно то, от чего
# граница слоёв и заведена. Список корневых имён этого не ловит: они
# `backend.*`, а не `sqlalchemy`.
ALLOWED_FROM_BACKEND = {"backend.model", "backend.config"}


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


def test_backend_does_not_import_client_or_qt():
    assert offenders("backend", BANNED_IN_BACKEND) == []


def test_client_does_not_import_storage_libraries():
    assert offenders("client", BANNED_IN_CLIENT) == []


def test_client_takes_only_the_boundary_types_from_the_backend():
    """Виджет, импортирующий сервис, лежит не там.

    Проверка по корневым именам это пропускает: `backend.storage.repository`
    — такой же `backend`, как и `backend.model`, а тянет за собой сессию
    SQLAlchemy и синхронный поход к базе мимо рантайма. Разделение слоёв
    перестаёт быть договорённостью только тогда, когда его проверяют целиком."""
    found = []
    for path in python_files("client"):
        for module in imported_modules(path):
            if not module.startswith("backend"):
                continue
            if any(module == name or module.startswith(name + ".")
                   for name in ALLOWED_FROM_BACKEND):
                continue
            found.append(f"{path.relative_to(ROOT)} → {module}")

    assert found == []
