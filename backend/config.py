from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DATA_DIR = "data"


@dataclass(frozen=True, slots=True)
class Config:
    data_dir: Path
    tmdb_key: str
    mdblist_key: str
    omdb_key: str
    poiskkino_key: str
    kinopoisk_unofficial_key: str
    log_level: str

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
        mdblist_key=value(env, "MDBLIST_API_KEY"),
        omdb_key=value(env, "OMDB_API_KEY"),
        poiskkino_key=value(env, "POISKKINO_API_KEY"),
        kinopoisk_unofficial_key=value(env, "KINOPOISK_UNOFFICIAL_API_KEY"),
        log_level=value(env, "LOG_LEVEL") or "INFO",
    )
