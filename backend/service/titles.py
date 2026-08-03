"""Приведение чужого названия к сравнимому виду.

Правила замерены 03.08.2026 на 1354 строках выдачи, и каждое убирает
расхождение, на котором две записи одной игры расходились ключом. Своим
модулем, а не внутри склейки: та решает, что с чем одна игра, а это — как
вообще сравнивать написания.
"""

import re
import unicodedata

# Римские до тринадцати: дальше в названиях игр они не встречаются, а `l`, `c` и
# `d` при разборе съели бы обычные слова.
ROMAN = {
    "i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7,
    "viii": 8, "ix": 9, "x": 10, "xi": 11, "xii": 12, "xiii": 13,
}

# Слова издания. Хвост из них снимается: издания одной игры — одна игра, решение
# пользователя 02.08.2026.
EDITION_WORDS = frozenset({
    "edition", "editions", "ed", "goty", "game", "of", "the", "year", "deluxe",
    "definitive", "enhanced", "complete", "ultimate", "gold", "premium",
    "anthology", "collection", "remastered", "remaster", "redux", "hd",
    "director", "directors", "cut", "special", "extended", "anniversary",
    "classic", "classics", "platinum", "legendary", "bundle", "pack",
    "trilogy", "collector", "collectors", "digital", "plus", "edycja", "full",
    "standard", "vr", "edt", "revised", "final", "master", "collected",
    "republic", "2in1",
})

# Знаки, которые надо заменить своими руками. Товарные — до `NFKC`: она
# разворачивает «™» в буквы «TM» и приклеивает их к слову, и «SOULS™»
# превратилось бы в «soulstm», то есть в новое слово.
SYMBOLS = str.maketrans({
    "™": " ", "®": " ", "©": " ", "℠": " ",
    "’": "'", "‘": "'", "–": "-", "—": "-", "…": " ", "²": "2", "³": "3",
})

ARTICLES = frozenset({"the", "a", "an"})


def flattened(name: str) -> str:
    """Плоское сравнимое написание, без снятия изданий.

    Знаки чистятся дважды — до и после `NFKC`: первая чистка спасает от
    разворачивания товарных знаков в буквы, вторая берёт то, что нормализация
    привела к своему виду."""
    if not name:
        return ""
    flat = name.translate(SYMBOLS)
    flat = unicodedata.normalize("NFKC", flat).translate(SYMBOLS).lower()
    # Союз к одному виду через промежуточный знак: иначе `and` из первой замены
    # снова стало бы словом во второй.
    flat = re.sub(r"\band\b", " & ", flat)
    flat = flat.replace("&", " and ")
    flat = re.sub(r"[^0-9a-zа-яё]+", " ", flat)
    words = [str(ROMAN[one]) if one in ROMAN else one for one in flat.split()]
    return " ".join(one for one in words if one not in ARTICLES)


def without_edition(name: str) -> str:
    """То же, но со снятым хвостом издательских слов.

    Снимается только хвост, а не слова где попало: «Game» посреди названия —
    обычное слово, и «The Game of Life» превратилась бы в «life».

    Название, состоящее из одних издательских слов, остаётся собой: пустой ключ
    склеил бы всё со всем."""
    words = flattened(name).split()
    while words and words[-1] in EDITION_WORDS:
        words.pop()
    return " ".join(words) or flattened(name)
