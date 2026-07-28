from pathlib import Path

from backend.config import load_config


def test_data_dir_defaults_to_folder_next_to_program(tmp_path):
    config = load_config({}, base_dir=tmp_path)
    assert config.data_dir == tmp_path / "data"


def test_data_dir_is_overridden_by_env(tmp_path):
    config = load_config({"DATA_DIR": str(tmp_path / "elsewhere")}, base_dir=tmp_path)
    assert config.data_dir == tmp_path / "elsewhere"


def test_blank_data_dir_falls_back_to_default(tmp_path):
    # В .env.example переменная объявлена пустой — это не «путь в никуда».
    config = load_config({"DATA_DIR": "   "}, base_dir=tmp_path)
    assert config.data_dir == tmp_path / "data"


def test_file_paths_sit_inside_data_dir(tmp_path):
    config = load_config({}, base_dir=tmp_path)
    assert config.library_db == tmp_path / "data" / "library.db"
    assert config.posters_db == tmp_path / "data" / "posters.db"
    assert config.log_file == tmp_path / "data" / "app.log"


# Значения нарочно разные: с одинаковыми перепутанные местами переменные
# окружения прошли бы молча, а ключ не от того источника — это отказ в ответе,
# который потом ищут в клиенте.
KEYS = {
    "TMDB_API_KEY": ("tmdb_key", "ключ-tmdb"),
    "MDBLIST_API_KEY": ("mdblist_key", "ключ-mdblist"),
    "OMDB_API_KEY": ("omdb_key", "ключ-omdb"),
    "POISKKINO_API_KEY": ("poiskkino_key", "ключ-poiskkino"),
    "KINOPOISK_UNOFFICIAL_API_KEY": ("kinopoisk_unofficial_key", "ключ-kinopoisk"),
}


def test_every_key_is_read_from_its_own_variable():
    config = load_config(
        {name: value for name, (_, value) in KEYS.items()}, base_dir=Path(".")
    )
    assert {field: getattr(config, field) for field, _ in KEYS.values()} == {
        field: value for field, value in KEYS.values()
    }


def test_missing_keys_are_empty():
    config = load_config({}, base_dir=Path("."))
    assert [getattr(config, field) for field, _ in KEYS.values()] == [""] * len(KEYS)


def test_keys_are_trimmed():
    # В .env пробел после `=` глазами не виден, а ключ с ним получает отказ.
    config = load_config({"TMDB_API_KEY": "  abc  "}, base_dir=Path("."))
    assert config.tmdb_key == "abc"


def test_log_level_is_read_from_env():
    assert load_config({"LOG_LEVEL": "DEBUG"}, base_dir=Path(".")).log_level == "DEBUG"


def test_log_level_defaults_to_info():
    assert load_config({}, base_dir=Path(".")).log_level == "INFO"
