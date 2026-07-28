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


def test_keys_are_read_and_missing_ones_are_empty():
    config = load_config({"TMDB_API_KEY": "abc"}, base_dir=Path("."))
    assert config.tmdb_key == "abc"
    assert config.omdb_key == ""


def test_log_level_defaults_to_info():
    assert load_config({}, base_dir=Path(".")).log_level == "INFO"
