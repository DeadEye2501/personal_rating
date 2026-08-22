"""Настройки приложения, прочитанные из окружения."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DATA_DIR = "data"

# Ступеней в своей оценке. Наружу из настроек идёт число, а не признак: весь
# остальной код говорит «пять» и «десять», а слово «удвоено» дальше не живёт.
TEN = 10
FIVE = 5


@dataclass(frozen=True, slots=True)
class Config:
    data_dir: Path
    tmdb_key: str
    google_books_key: str
    mdblist_key: str
    omdb_key: str
    poiskkino_key: str
    kinopoisk_unofficial_key: str
    log_level: str
    scale: int

    @property
    def library_db(self) -> Path:
        return self.data_dir / "library.db"

    @property
    def posters_db(self) -> Path:
        return self.data_dir / "posters.db"

    @property
    def log_file(self) -> Path:
        return self.data_dir / "app.log"


def value(env: Mapping[str, str], name: str) -> str:
    """Значение без краёв. В `.env` пробел после `=` не виден глазами, а ключ
    с пробелом — это отказ источника, который потом ищут в клиенте."""
    return env.get(name, "").strip()


def load_config(env: Mapping[str, str], base_dir: Path) -> Config:
    override = value(env, "DATA_DIR")
    return Config(
        data_dir=Path(override) if override else base_dir / DEFAULT_DATA_DIR,
        tmdb_key=value(env, "TMDB_API_KEY"),
        google_books_key=value(env, "GOOGLE_BOOKS_API_KEY"),
        mdblist_key=value(env, "MDBLIST_API_KEY"),
        omdb_key=value(env, "OMDB_API_KEY"),
        poiskkino_key=value(env, "POISKKINO_API_KEY"),
        kinopoisk_unofficial_key=value(env, "KINOPOISK_UNOFFICIAL_API_KEY"),
        log_level=value(env, "LOG_LEVEL") or "INFO",
        # Ступеней всегда десять, кроме единственного явного «нет»: опечатка в
        # переменной обязана оставить шкалу привычной, а не переписать всю
        # библиотеку — пересчёт необратим.
        scale=FIVE if value(env, "SCALE_X2") == "0" else TEN,
    )
