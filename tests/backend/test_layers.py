import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

BANNED_IN_CLIENT = {"sqlalchemy", "aiosqlite", "httpx", "alembic", "PIL"}

# Из бэкенда клиенту открыты только типы границы и настройки. Всё прочее —
# репозитории, сервисы, клиенты источников — тянет за собой и сессию
# SQLAlchemy, и поход к диску в главном потоке, то есть ровно то, от чего
# граница слоёв и заведена. Список корневых имён этого не ловит: они
# `backend.*`, а не `sqlalchemy`.
ALLOWED_FROM_BACKEND = {"backend.model", "backend.config", "backend.app"}


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


def offenders(package: str, banned: set[str]) -> list[str]:
    # Без этой проверки тест тихо зеленеет на отсутствующей папке: rglob по
    # несуществующему пути отдаёт пустоту, а не исключение.
    assert (ROOT / package).is_dir(), f"нет пакета {package}"

    found = []
    for path in sorted((ROOT / package).rglob("*.py")):
        for root in imported_roots(path):
            if root in banned:
                found.append(f"{path.relative_to(ROOT)} → {root}")
    return found


def test_backend_does_not_import_client():
    assert offenders("backend", {"client"}) == []


def test_client_does_not_import_storage_libraries():
    assert offenders("client", BANNED_IN_CLIENT) == []


def test_client_takes_only_the_boundary_types_from_the_backend():
    """Виджет, импортирующий сервис, лежит не там.

    Проверка по корневым именам это пропускает: `backend.model.link` —
    такой же `backend`, как и `backend.model`, а тянет за собой репозитории,
    сессию и синхронный поход к базе мимо рантайма. Разделение слоёв
    перестаёт быть договорённостью только тогда, когда его проверяют целиком."""
    assert (ROOT / "client").is_dir(), "нет пакета client"

    found = []
    for path in sorted((ROOT / "client").rglob("*.py")):
        for module in imported_modules(path):
            if not module.startswith("backend"):
                continue
            if any(module == name or module.startswith(name + ".")
                   for name in ALLOWED_FROM_BACKEND):
                continue
            found.append(f"{path.relative_to(ROOT)} → {module}")

    assert found == []
