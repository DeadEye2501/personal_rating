"""Обрезка залитой руками картинки до формы обложки."""

import io

import pytest
from PIL import Image

from backend.model import Kind
from backend.service.images import (
    TARGET_SIZE,
    BadImage,
    crop_to_cover,
)
from tests.conftest import picture, size_of


def painted(size: tuple[int, int], band: tuple[int, int, int, int]) -> bytes:
    """Чёрная картинка с красной полосой в указанном прямоугольнике."""
    source = Image.new("RGB", size, (0, 0, 0))
    source.paste((255, 0, 0), band)
    buffer = io.BytesIO()
    source.save(buffer, format="PNG")
    return buffer.getvalue()


def red_box(data: bytes) -> tuple[int, int, int, int] | None:
    """Границы красного в результате или `None`, если красного не осталось.

    Порог, а не точное равенство: результат — JPEG, и края полосы он размывает."""
    red, _, _ = Image.open(io.BytesIO(data)).convert("RGB").split()
    return red.point(lambda value: 255 if value > 200 else 0).getbbox()


def test_an_uploaded_album_cover_is_cropped_to_a_square():
    """У альбома обложка квадратная — у Deezer 1000×1000, — и афишная обрезка
    срезала бы ей бока. Наблюдается размером на выходе, а не константой:
    константу тест повторил бы, а не проверил."""
    out = size_of(crop_to_cover(picture(2000, 1000), Kind.MUSIC))

    assert out[0] == out[1]


def test_an_uploaded_book_cover_is_still_a_poster():
    """Половина, которая осталась правдой: у кино, книг и игр обложка 2:3, и
    квадрат для них — поломка, а не выбор."""
    width, height = size_of(crop_to_cover(picture(2000, 1000), Kind.BOOK))

    assert round(width / height, 3) == round(2 / 3, 3)


def test_a_square_keeps_the_middle_of_a_wide_picture():
    """Режется поровну с боков, как у афиши: смещённая обрезка увела бы центр
    обложки вбок, и у альбома это видно сразу — там обычно лицо или знак.

    Наблюдается симметрией полосы, а не тем, что красное уцелело: уцелеет оно и
    при обрезке в левый край — полоса стоит по центру широкой картинки, а
    квадрат из неё вырезается шириной в половину."""
    wide = painted((1000, 500), (450, 0, 550, 500))

    square = crop_to_cover(wide, Kind.MUSIC)
    left, _, right, _ = red_box(square)

    assert abs(left - (size_of(square)[0] - right)) <= 2, "полоса не по центру"


def test_a_square_is_cut_by_its_ratio_and_not_by_the_squeeze():
    """Квадрат даёт **пропорция обрезки**, а не размер на выходе.

    Стороны равными выйдут в любом случае: `crop_to_cover` ужимает вырезанное до
    `SQUARE_SIZE`, и афишная обрезка просто сплющилась бы в квадрат — с
    обрезанными боками и растянутым содержимым. Поэтому наблюдается доля полосы,
    а не размер: квадрат берёт от широкой картинки половину ширины, и полоса
    шириной в десятую занимает в нём пятую часть, а афишная обрезка взяла бы
    треть.

    Соседняя проверка размера этого не различает вовсе — на ней и держалась
    единственная сторожевая нить квадрата."""
    wide = painted((1000, 500), (450, 0, 550, 500))

    square = crop_to_cover(wide, Kind.MUSIC)
    left, _, right, _ = red_box(square)
    share = (right - left) / size_of(square)[0]

    assert 0.17 <= share <= 0.23, f"полоса заняла {share:.2f} вместо пятой части"


def test_the_target_size_is_five_hundred_by_seven_fifty():
    """Единственное место, где размер написан литералом: остальные сверяют его с
    `TARGET_SIZE`, то есть с самим объявлением, и переедут вместе с ним. А выбран
    он не на глаз — это w500 у TMDB, из которого спека считает ~80 КБ на постер."""
    assert size_of(crop_to_cover(picture(2000, 1000), Kind.MOVIE)) == (500, 750)


def test_the_square_size_is_five_hundred_by_five_hundred():
    """Второй размер литералом, и по той же причине, что первый: остальные
    сверяют его с `SQUARE_SIZE`, то есть с самим объявлением.

    Взят он от той же мерки, из которой спека считает хранилище: обложка
    альбома вдвое больше по стороне занимала бы вчетверо больше места, а
    равенство сторон — единственное, что у квадрата сторожили до сих пор, — от
    такой подмены не меняется вовсе."""
    assert size_of(crop_to_cover(picture(2000, 1000), Kind.MUSIC)) == (500, 500)


def test_a_wide_picture_comes_out_the_target_size():
    assert size_of(crop_to_cover(picture(2000, 1000), Kind.MOVIE)) == TARGET_SIZE


def test_a_tall_picture_comes_out_the_target_size():
    assert size_of(crop_to_cover(picture(1000, 4000), Kind.MOVIE)) == TARGET_SIZE


def test_an_already_correct_ratio_is_only_resized():
    assert size_of(crop_to_cover(picture(600, 900), Kind.MOVIE)) == TARGET_SIZE


def test_a_full_size_cover_weighs_about_what_the_storage_counts_on():
    """Качество сжатия выбрано под арифметику хранилища: спека считает его из
    примерно 80 КБ на постер, а фотография с телефона эту арифметику ломает.

    Наблюдается весом, потому что весом оно и выбрано: у качества нет другого
    следствия, ради которого его ставили.

    Границы замерены на этой самой картинке 23.08.2026: при 88 она весит 81 КБ,
    при 75 (умолчание Pillow, то есть потерянный довод) — 60, при 95 — 108, при
    30 — 33. Ловится отсюда и потеря довода, и всякий заметный сдвиг; соседние
    ступени, 85 и 90, не ловятся нарочно — вес зависит ещё и от версии Pillow, и
    сторож на две ступени краснел бы от чужого обновления.

    Картинка рисуется шумом нарочно: одноцветная сжимается в пару килобайт при
    любом качестве и не различает ничего."""
    noisy = Image.new("RGB", (500, 750))
    pixels = noisy.load()
    for x in range(500):
        for y in range(750):
            pixels[x, y] = ((x * 7) % 256, (y * 5) % 256, ((x + y) * 3) % 256)
    buffer = io.BytesIO()
    noisy.save(buffer, format="PNG")

    weight = len(crop_to_cover(buffer.getvalue(), Kind.MOVIE))

    assert 72_000 <= weight <= 92_000, f"обложка весит {weight // 1024} КБ"


def test_a_small_picture_is_not_blown_up():
    """Растягивать маленькую картинку незачем: она станет только хуже."""
    assert size_of(crop_to_cover(picture(200, 300), Kind.MOVIE)) == (200, 300)


def test_a_small_picture_is_still_cropped_to_shape():
    """Мелкую не растягиваем, но форму ей правим: не растягивать и не обрезать —
    разные решения, и второе относится к любому размеру."""
    assert size_of(crop_to_cover(picture(400, 300), Kind.MOVIE)) == (200, 300)


def test_the_sides_are_trimmed_equally():
    """Широкой режем бока поровну: остаётся центр, а не левый край. Полоса из
    середины исходника обязана остаться в середине результата."""
    data = crop_to_cover(painted((900, 300), (400, 0, 500, 300)), Kind.MOVIE)
    box = red_box(data)
    assert box is not None, "красная полоса из центра исходника потерялась"

    left, _, right, _ = box
    assert abs(left - (size_of(data)[0] - right)) <= 2, "полоса уехала от центра"


def test_the_top_and_bottom_are_trimmed_equally():
    """То же для высокой: срезается сверху и снизу поровну."""
    data = crop_to_cover(painted((300, 900), (0, 400, 300, 500)), Kind.MOVIE)
    box = red_box(data)
    assert box is not None, "красная полоса из центра исходника потерялась"

    _, top, _, bottom = box
    assert abs(top - (size_of(data)[1] - bottom)) <= 2, "полоса уехала от центра"


def test_jpeg_is_accepted_too():
    assert size_of(crop_to_cover(picture(1200, 1800, fmt="JPEG"), Kind.MOVIE)) == TARGET_SIZE


def test_transparency_does_not_break_the_conversion():
    buffer = io.BytesIO()
    Image.new("RGBA", (1200, 1800), (10, 20, 30, 128)).save(buffer, format="PNG")
    assert size_of(crop_to_cover(buffer.getvalue(), Kind.MOVIE)) == TARGET_SIZE


@pytest.mark.parametrize("fmt", ["PNG", "JPEG"])
def test_the_result_is_always_the_same_format(fmt):
    """Чтобы интерфейс не гадал, что ему приехало."""
    data = crop_to_cover(picture(1200, 1800, fmt=fmt), Kind.MOVIE)
    assert Image.open(io.BytesIO(data)).format == "JPEG"


DEGENERATE = [
    ((1, 1), (1, 1)),
    ((3000, 10), (7, 10)),
    ((10, 3000), (10, 15)),
]


@pytest.mark.parametrize(("source", "expected"), DEGENERATE)
def test_degenerate_shapes_come_out_as_close_to_2_3_as_integers_allow(source,
                                                                     expected):
    """Полоска в три тысячи пикселей шириной — тоже картинка, и считается ей
    обрезка тем же способом. Размер называется целиком: «не упало» не отличит
    правильную обрезку от любой другой."""
    assert size_of(crop_to_cover(picture(*source), Kind.MOVIE)) == expected


def test_a_half_written_file_is_a_named_error_too():
    """Обрезанный на середине PNG разбирается по шапке и ломается на пикселях:
    заголовку верить нельзя, картинку надо прочитать целиком."""
    with pytest.raises(BadImage):
        crop_to_cover(picture(1200, 1800)[:200], Kind.MOVIE)


def test_an_odd_side_is_rounded_and_not_truncated():
    """Нечётная сторона даёт половину пикселя, и она округляется вверх, а не
    отбрасывается: иначе высокая картинка систематически теряла бы лишнюю
    строку сверху или снизу."""
    assert size_of(crop_to_cover(picture(301, 900), Kind.MOVIE)) == (301, 452)


@pytest.mark.parametrize("data", [b"", "это не картинка".encode()],
                         ids=["empty", "garbage"])
def test_bytes_that_are_not_a_picture_are_a_named_error(data):
    with pytest.raises(BadImage):
        crop_to_cover(data, Kind.MOVIE)
