import io

import pytest
from PIL import Image

from backend.service.images import TARGET_SIZE, BadImage, crop_to_cover
from tests.conftest import picture


def painted(size: tuple[int, int], band: tuple[int, int, int, int]) -> bytes:
    """Чёрная картинка с красной полосой в указанном прямоугольнике."""
    source = Image.new("RGB", size, (0, 0, 0))
    source.paste((255, 0, 0), band)
    buffer = io.BytesIO()
    source.save(buffer, format="PNG")
    return buffer.getvalue()


def size_of(data: bytes) -> tuple[int, int]:
    return Image.open(io.BytesIO(data)).size


def red_box(data: bytes) -> tuple[int, int, int, int] | None:
    """Границы красного в результате или `None`, если красного не осталось.

    Порог, а не точное равенство: результат — JPEG, и края полосы он размывает."""
    red, _, _ = Image.open(io.BytesIO(data)).convert("RGB").split()
    return red.point(lambda value: 255 if value > 200 else 0).getbbox()


def test_a_wide_picture_comes_out_the_target_size():
    assert size_of(crop_to_cover(picture(2000, 1000))) == TARGET_SIZE


def test_a_tall_picture_comes_out_the_target_size():
    assert size_of(crop_to_cover(picture(1000, 4000))) == TARGET_SIZE


def test_an_already_correct_ratio_is_only_resized():
    assert size_of(crop_to_cover(picture(600, 900))) == TARGET_SIZE


def test_a_small_picture_is_not_blown_up():
    """Растягивать маленькую картинку незачем: она станет только хуже."""
    assert size_of(crop_to_cover(picture(200, 300))) == (200, 300)


def test_a_small_picture_is_still_cropped_to_shape():
    """Мелкую не растягиваем, но форму ей правим: не растягивать и не обрезать —
    разные решения, и второе относится к любому размеру."""
    assert size_of(crop_to_cover(picture(400, 300))) == (200, 300)


def test_the_sides_are_trimmed_equally():
    """Широкой режем бока поровну: остаётся центр, а не левый край. Полоса из
    середины исходника обязана остаться в середине результата."""
    data = crop_to_cover(painted((900, 300), (400, 0, 500, 300)))
    box = red_box(data)
    assert box is not None, "красная полоса из центра исходника потерялась"

    left, _, right, _ = box
    assert abs(left - (size_of(data)[0] - right)) <= 2, "полоса уехала от центра"


def test_the_top_and_bottom_are_trimmed_equally():
    """То же для высокой: срезается сверху и снизу поровну."""
    data = crop_to_cover(painted((300, 900), (0, 400, 300, 500)))
    box = red_box(data)
    assert box is not None, "красная полоса из центра исходника потерялась"

    _, top, _, bottom = box
    assert abs(top - (size_of(data)[1] - bottom)) <= 2, "полоса уехала от центра"


def test_jpeg_is_accepted_too():
    assert size_of(crop_to_cover(picture(1200, 1800, fmt="JPEG"))) == TARGET_SIZE


def test_transparency_does_not_break_the_conversion():
    buffer = io.BytesIO()
    Image.new("RGBA", (1200, 1800), (10, 20, 30, 128)).save(buffer, format="PNG")
    assert size_of(crop_to_cover(buffer.getvalue())) == TARGET_SIZE


@pytest.mark.parametrize("fmt", ["PNG", "JPEG"])
def test_the_result_is_always_the_same_format(fmt):
    """Чтобы интерфейс не гадал, что ему приехало."""
    data = crop_to_cover(picture(1200, 1800, fmt=fmt))
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
    assert size_of(crop_to_cover(picture(*source))) == expected


def test_a_half_written_file_is_a_named_error_too():
    """Обрезанный на середине PNG разбирается по шапке и ломается на пикселях:
    заголовку верить нельзя, картинку надо прочитать целиком."""
    with pytest.raises(BadImage):
        crop_to_cover(picture(1200, 1800)[:200])


def test_an_odd_side_is_rounded_and_not_truncated():
    """Нечётная сторона даёт половину пикселя, и она округляется вверх, а не
    отбрасывается: иначе высокая картинка систематически теряла бы лишнюю
    строку сверху или снизу."""
    assert size_of(crop_to_cover(picture(301, 900))) == (301, 452)


@pytest.mark.parametrize("data", [b"", "это не картинка".encode()],
                         ids=["empty", "garbage"])
def test_bytes_that_are_not_a_picture_are_a_named_error(data):
    with pytest.raises(BadImage):
        crop_to_cover(data)
