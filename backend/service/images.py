"""Приведение залитой с диска картинки к виду обложки."""

import io

from PIL import Image, UnidentifiedImageError

from backend.model import BadImage

TARGET_RATIO = 2 / 3
# Размер взят из w500 у TMDB: спека называет только пропорцию, но считает
# хранилище из ~80 КБ на постер, а фотография с телефона ломает эту арифметику.
TARGET_SIZE = (500, 750)

_QUALITY = 88


def _centred_box(width: int, height: int) -> tuple[int, int, int, int]:
    """Что оставить от картинки: середину, обрезанную до 2:3.

    Режется поровну с двух сторон — широкой бока, высокой верх и низ."""
    if width / height > TARGET_RATIO:
        keep = round(height * TARGET_RATIO)
        left = (width - keep) // 2
        return (left, 0, left + keep, height)
    keep = round(width / TARGET_RATIO)
    top = (height - keep) // 2
    return (0, top, width, top + keep)


def crop_to_cover(data: bytes) -> bytes:
    """Обрезка по центру до 2:3 и ужатие до `TARGET_SIZE`.

    Только для залитых с диска картинок: скачанные постеры уже 2:3, и
    перекодировать их незачем.

    Маленькую картинку не растягиваем: от этого она только хуже."""
    try:
        source = Image.open(io.BytesIO(data))
        source.load()
    except (UnidentifiedImageError, OSError) as error:
        raise BadImage(str(error)) from error

    cropped = source.convert("RGB").crop(_centred_box(*source.size))
    if cropped.width > TARGET_SIZE[0]:
        cropped = cropped.resize(TARGET_SIZE, Image.Resampling.LANCZOS)

    buffer = io.BytesIO()
    cropped.save(buffer, format="JPEG", quality=_QUALITY, optimize=True)
    return buffer.getvalue()
