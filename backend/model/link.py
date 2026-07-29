"""Разобранная ссылка на страницу во внешней базе."""

import re
from dataclasses import dataclass

from backend.model.kinds import Kind, Source


@dataclass(frozen=True, slots=True)
class ExternalLink:
    source: Source
    source_id: str
    kind: Kind


# Хвосты вроде -interstellar и параметры после ? отбрасываются: идентификатор
# кончается там, где кончаются цифры.
# Регистр не важен: человек вставляет то, что скопировал, а адресная строка и
# почтовые клиенты любят поднимать первую букву — «GOG.com» ломало бы разбор.
_TMDB = re.compile(r"themoviedb\.org/(movie|tv)/(\d+)", re.I)
# `agecheck/` — возрастной шлюз: у игр с ним именно этот адрес стоит в строке
# браузера, и без него разбор промахивается по половине ретро.
_STEAM = re.compile(r"store\.steampowered\.com/(?:agecheck/)?app/(\d+)", re.I)
# У GOG в адресе не идентификатор, а слаг: числовой придётся искать в каталоге.
# Необязательный сегмент — язык: `gog.com/en/game/...` приходит из письма.
_GOG = re.compile(r"gog\.com/(?:[a-z-]+/)?game/([a-z0-9_]+)", re.I)
_BARE = re.compile(r"^\d+$")

_TMDB_KINDS = {"movie": Kind.MOVIE, "tv": Kind.SERIES}
_FILMS = (Kind.MOVIE, Kind.SERIES)


def parse_link(raw: str, kind: Kind | None = None) -> ExternalLink | None:
    """`kind` — то, что выбрано тумблером. Ссылка его перебивает: она знает
    точнее."""
    # Пробелы обрезаются ради голого числа: адрес нашёлся бы и в строке с ними,
    # а `^\d+$` — нет. Отдельной проверки на пустую строку не нужно: ни один
    # образец в неё не попадает.
    text = raw.strip()

    found = _TMDB.search(text)
    if found:
        # Слово пути приводится к нижнему регистру: образец нечувствителен к
        # нему, а таблица — нет, и «/Movie/» падало бы на поиске в ней.
        return ExternalLink(source=Source.TMDB, source_id=found.group(2),
                            kind=_TMDB_KINDS[found.group(1).lower()])

    found = _STEAM.search(text)
    if found:
        return ExternalLink(source=Source.STEAM, source_id=found.group(1),
                            kind=Kind.GAME)

    found = _GOG.search(text)
    if found:
        # Слаг приводится к нижнему регистру: он и есть идентичность карточки, а
        # в каталоге GOG он всегда строчный. Вставленный с заглавными, он завёл
        # бы той же игре вторую личность.
        return ExternalLink(source=Source.GOG, source_id=found.group(1).lower(),
                            kind=Kind.GAME)

    # Голое число значит что-то только у кино: там источник один. У игр Steam и
    # GOG нумеруются независимо, и по числу их не различить.
    if _BARE.match(text) and kind in _FILMS:
        return ExternalLink(source=Source.TMDB, source_id=text, kind=kind)

    return None
