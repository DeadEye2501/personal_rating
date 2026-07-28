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


def load_config(env: Mapping[str, str], base_dir: Path) -> Config:
    override = env.get("DATA_DIR", "").strip()
    return Config(
        data_dir=Path(override) if override else base_dir / DEFAULT_DATA_DIR,
        tmdb_key=env.get("TMDB_API_KEY", ""),
        mdblist_key=env.get("MDBLIST_API_KEY", ""),
        omdb_key=env.get("OMDB_API_KEY", ""),
        poiskkino_key=env.get("POISKKINO_API_KEY", ""),
        kinopoisk_unofficial_key=env.get("KINOPOISK_UNOFFICIAL_API_KEY", ""),
        log_level=env.get("LOG_LEVEL", "").strip() or "INFO",
    )
