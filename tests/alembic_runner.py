"""Запуск миграций из теста."""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def alembic(db_path: Path, *command: str) -> None:
    """Миграции гоняются как их гоняет человек — отдельным процессом, по
    временной базе: `-x db=` для того и заведён."""
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-x", f"db={db_path}", *command],
        cwd=ROOT, capture_output=True, text=True,
    )
    if result.returncode != 0:
        joined = " ".join(command)
        pytest.fail(f"alembic {joined} провалился:\n{result.stdout}\n{result.stderr}")
