"""Хранилище постеров вторым файлом базы."""

from datetime import datetime, timedelta

from sqlalchemy import select

from backend.storage.posters import PosterStore, poster
from backend.storage.session import create_engine
from tests.conftest import PICTURE
from tests.conftest import MOMENT as WHEN

# Байтовый литерал не держит кириллицу — только через encode().
OTHER = "другая обложка".encode()


async def test_put_and_get(posters):
    await posters.put(1, PICTURE, now=WHEN)
    assert await posters.get(1) == PICTURE


async def test_bytes_come_back_exactly_as_written(posters):
    """Картинка — байты, а не текст: пройди она через кодировку, PNG перестал
    бы открываться, а длина осталась бы похожей."""
    await posters.put(1, PICTURE, now=WHEN)

    stored = await posters.get(1)
    assert isinstance(stored, bytes)
    assert stored[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(stored) == len(PICTURE)


async def test_pictures_of_different_cards_do_not_mix(posters):
    await posters.put(1, PICTURE, now=WHEN)
    await posters.put(2, OTHER, now=WHEN)

    assert await posters.get(2) == OTHER
    assert await posters.get(1) == PICTURE


async def test_missing_poster_is_not_an_error(posters):
    """Хранилище нарочно непустое: на пустом «нет такой картинки» и «нет ни
    одной» неразличимы, и проверка без сравнения с карточкой прошла бы молча."""
    await posters.put(5, PICTURE, now=WHEN)

    # Спрашиваем про номер меньше лежащего: сравнение «больше или равно»
    # вместо «равно» на паре 1 и 999 прошло бы молча.
    assert await posters.get(1) is None
    assert await posters.has(1) is False


async def test_a_stored_poster_is_there(posters):
    """Обратная половина к «нет постера»: `has` обязан отвечать «да», когда
    картинка есть, иначе постоянное «нет» прошло бы проверку."""
    await posters.put(1, PICTURE, now=WHEN)
    assert await posters.has(1) is True


async def test_second_put_replaces_the_picture(posters):
    await posters.put(1, PICTURE, now=WHEN)
    await posters.put(1, OTHER, now=WHEN)
    assert await posters.get(1) == OTHER


async def test_second_put_moves_the_fetch_time(posters, tmp_path):
    """Время в строке — время этих байтов, а не первых: заменили картинку,
    значит и время её."""
    later = WHEN + timedelta(days=30)
    await posters.put(1, PICTURE, now=WHEN)
    await posters.put(1, OTHER, now=later)

    engine = create_engine(tmp_path / "posters.db")
    async with engine.connect() as connection:
        stored = await connection.execute(
            select(poster.c.fetched_at).where(poster.c.item_id == 1)
        )
        assert stored.scalar() == later
    await engine.dispose()


async def test_the_fetch_time_comes_back_a_time(posters, tmp_path):
    """Колонка объявлена временем, а не текстом: строкой она бы вернулась
    строкой, и сравнение с датой перестало бы что-либо значить."""
    await posters.put(1, PICTURE, now=WHEN)

    engine = create_engine(tmp_path / "posters.db")
    async with engine.connect() as connection:
        stored = await connection.execute(
            select(poster.c.fetched_at).where(poster.c.item_id == 1)
        )
        assert isinstance(stored.scalar(), datetime)
    await engine.dispose()


async def test_the_store_makes_its_folder(tmp_path):
    """Каталога данных при первом запуске ещё нет. Заводит его общий движок —
    и хранилище постеров обязано ходить через него, а не заводить свой."""
    store = PosterStore(tmp_path / "data" / "картинки" / "posters.db")
    await store.open()
    await store.put(1, PICTURE, now=WHEN)
    assert await store.get(1) == PICTURE
    await store.close()


async def test_delete(posters):
    await posters.put(1, PICTURE, now=WHEN)
    await posters.delete(1)
    assert await posters.has(1) is False


async def test_delete_takes_only_the_asked_picture(posters):
    """Удаляется не первая попавшаяся: снимаем вторую, первая обязана
    остаться."""
    await posters.put(1, PICTURE, now=WHEN)
    await posters.put(2, OTHER, now=WHEN)

    await posters.delete(2)

    assert await posters.get(1) == PICTURE
    assert await posters.has(2) is False


async def test_deleting_what_is_not_there_is_quiet(posters):
    await posters.delete(999)


async def test_store_lives_in_its_own_file(tmp_path):
    # Своя, а не общая фикстура: проверяется именно раскладка файлов.
    store = PosterStore(tmp_path / "posters.db")
    await store.open()
    await store.put(1, PICTURE, now=WHEN)
    await store.close()
    assert (tmp_path / "posters.db").exists()
    assert not (tmp_path / "library.db").exists()


async def test_a_closed_store_lets_go_of_its_file(tmp_path):
    """Закрытие отпускает файл: на Windows незакрытая база не удаляется, и
    забытый `dispose` виден именно этим, а не ошибкой при чтении."""
    path = tmp_path / "posters.db"
    store = PosterStore(path)
    await store.open()
    await store.put(1, PICTURE, now=WHEN)
    await store.close()

    path.unlink()
    assert not path.exists()


async def test_opening_twice_does_not_lose_the_first_engine(tmp_path):
    """Повторное открытие закрывает прежний движок, а не бросает его: иначе
    соединение остаётся висеть, и файл после `close` всё равно занят."""
    path = tmp_path / "posters.db"
    store = PosterStore(path)
    await store.open()
    await store.open()
    await store.put(1, PICTURE, now=WHEN)
    await store.close()

    path.unlink()
    assert not path.exists()


async def test_pictures_survive_a_reopen(tmp_path):
    """Хранилище — файл, а не память: закрыли и открыли снова, картинка на
    месте."""
    path = tmp_path / "posters.db"
    store = PosterStore(path)
    await store.open()
    await store.put(1, PICTURE, now=WHEN)
    await store.close()

    again = PosterStore(path)
    await again.open()
    assert await again.get(1) == PICTURE
    await again.close()
