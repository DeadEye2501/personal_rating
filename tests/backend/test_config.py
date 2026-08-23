"""Чтение настроек из окружения и путей к файлам данных."""

from pathlib import Path

import pytest

from backend.config import FIVE, TEN, load_config


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
#
# Google Books в таблице нет: у него ключей несколько, и поле не строка, а
# список. Его читает свой тест ниже.
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


def test_google_books_takes_its_keys_in_order():
    """Ключей у Google Books бывает два, и порядок значим: первым спрашивают,
    вторым продлевают день, когда суточная квота первого кончилась.

    Порядок наблюдается значениями, а не длиной: перепутай их местами — и
    запасной ключ тратился бы первым, а основной ждал бы полуночи."""
    config = load_config({"GOOGLE_BOOKS_API_KEY": "ключ-основной",
                          "GOOGLE_BOOKS_API_KEY_2": "ключ-запасной"},
                         base_dir=Path("."))

    assert config.google_books_keys == ("ключ-основной", "ключ-запасной")


def test_a_single_google_books_key_stays_alone():
    """Второй ключ необязателен: не вписан — источник работает с одним, как
    работал до появления запасного. Пустая строка ключом не считается — с ней
    Google отвечает отказом, и место в списке она заняла бы зря."""
    config = load_config({"GOOGLE_BOOKS_API_KEY": "ключ-основной",
                          "GOOGLE_BOOKS_API_KEY_2": "  "}, base_dir=Path("."))

    assert config.google_books_keys == ("ключ-основной",)
    assert load_config({}, base_dir=Path(".")).google_books_keys == ()


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


@pytest.mark.parametrize(("given", "steps"), [
    ("0", FIVE), ("1", TEN), ("", TEN), ("да", TEN), (" 0 ", FIVE),
])
def test_the_scale_is_ten_unless_the_variable_says_otherwise(tmp_path, given,
                                                             steps):
    """Ступеней всегда десять, кроме единственного явного «нет»: опечатка в
    переменной обязана оставить шкалу привычной, а не переписать всю
    библиотеку — пересчёт необратим."""
    assert load_config({"SCALE_X2": given}, base_dir=tmp_path).scale == steps


def test_a_missing_variable_leaves_the_usual_scale(tmp_path):
    """Переменной нет вовсе — это `.env` от прежней версии, и шкала в нём
    десятибалльная."""
    assert load_config({}, base_dir=tmp_path).scale == TEN
