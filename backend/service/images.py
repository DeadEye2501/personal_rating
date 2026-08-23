"""Приведение залитой с диска картинки к виду обложки."""

import io

from PIL import Image, UnidentifiedImageError

from backend.model import BadImage, Kind

TARGET_RATIO = 2 / 3
# Размер взят из w500 у TMDB: спека называет только пропорцию, но считает
# хранилище из ~80 КБ на постер, а фотография с телефона ломает эту арифметику.
TARGET_SIZE = (500, 750)

# У альбома обложка квадратная: у Deezer она 1000×1000, и афишная рамка срезала
# бы ей бока. Второй парой констант, а не своим типом: у формы обложки ровно два
# читателя — `_shape` здесь и признак квадрата во фронте, — и третьего не
# предвидится.
SQUARE_RATIO = 1.0
SQUARE_SIZE = (500, 500)

_QUALITY = 88


def _shape(kind: Kind) -> tuple[float, tuple[int, int]]:
    """Пропорция и размер обложки этого типа содержимого."""
    return ((SQUARE_RATIO, SQUARE_SIZE) if kind is Kind.MUSIC
            else (TARGET_RATIO, TARGET_SIZE))


def _centred_box(width: int, height: int,
                 ratio: float) -> tuple[int, int, int, int]:
    """Что оставить от картинки: середину, обрезанную до нужной пропорции.

    Режется поровну с двух сторон — широкой бока, высокой верх и низ.
    Пропорция приезжает доводом, а не читается из модуля: иначе она стала бы
    вторым местом, где живёт то же знание, и у музыки разъехалась бы молча."""
    if width / height > ratio:
        keep = round(height * ratio)
        left = (width - keep) // 2
        return (left, 0, left + keep, height)
    keep = round(width / ratio)
    top = (height - keep) // 2
    return (0, top, width, top + keep)


def already_shaped(data: bytes, kind: Kind) -> bool:
    """Пришла ли картинка уже в нашей форме — то есть резать ей нечего.

    Спрашивает скачанное: у TMDB, Steam, GOG и Deezer обложка приходит ровно
    2:3 или ровно квадратом, и перекодировать её значило бы потерять качество и
    запас под высокую плотность экрана. У Google Books формы нет вовсе — 1808×2552
    у одной книги, 128×194 у другой, — и такую обложку обрезка обязана привести.

    Считается тем же `_centred_box`, что и сама обрезка: второе место, где живёт
    та же арифметика, разошлось бы с первым молча."""
    ratio, _ = _shape(kind)
    try:
        with Image.open(io.BytesIO(data)) as source:
            width, height = source.size
    except (UnidentifiedImageError, OSError):
        # Не прочиталась — значит резать нечего, и это не отговорка: путь
        # скачанного и раньше отдавал байты как есть, а решать за источник по
        # тому, чего не смогли открыть, не наше дело. Настоящую беду увидит тот,
        # кто картинку покажет.
        return True
    return _centred_box(width, height, ratio) == (0, 0, width, height)


def crop_to_cover(data: bytes, kind: Kind) -> bytes:
    """Обрезка по центру до формы обложки этого типа и ужатие до её размера.

    У кино, книг и игр это 2:3, у музыки квадрат. Тип обязателен, а не
    подставляется умолчанием: забытый довод молча срезал бы альбому бока, и
    заметить это можно было бы только глазами.

    Зовут её оба пути: залитую с диска картинку она обрезает всегда, скачанную —
    только когда форма чужая (`already_shaped`). Так у Google Books и
    old-games.ru, у остальных обложка приходит нашей формы и не перекодируется.

    Маленькую картинку не растягиваем: от этого она только хуже."""
    ratio, size = _shape(kind)
    try:
        source = Image.open(io.BytesIO(data))
        source.load()
    except (UnidentifiedImageError, OSError) as error:
        raise BadImage(str(error)) from error

    cropped = source.convert("RGB").crop(_centred_box(*source.size, ratio))
    if cropped.width > size[0]:
        cropped = cropped.resize(size, Image.Resampling.LANCZOS)

    buffer = io.BytesIO()
    cropped.save(buffer, format="JPEG", quality=_QUALITY, optimize=True)
    return buffer.getvalue()
