"""Перевод ответов FantLab в наши типы."""

from backend.titles import flattened

__all__ = ["edition_of"]


def edition_of(payload: dict, isbn: str, title: str) -> int | None:
    """Номер издания, у которого сошлись **оба** признака: ISBN и название.

    Двумя, а не одним, и это решение пользователя 23.08.2026. Каждый по
    отдельности врёт:

    - **поиск у FantLab полнотекстовый**, а не по полю: на запрошенный ISBN
      «Пикника на обочине» он вернул «Властелин Колец. Хранители Кольца» —
      замерено 23.08.2026, и разведка это же видела на четырёх строках из
      семнадцати;
    - **ISBN у Google местами чужой**: `9785041684464` числится за «Властелином
      Колец», а ведёт на «Снежный сон» Трониной — подтверждено тремя
      источниками независимо.

    Сойдясь вместе, они друг друга и страхуют: чужой ISBN не пройдёт по
    названию, чужая строка поиска — по номеру.

    У издания бывает несколько ISBN разом — «978-5-271-46168-2, 978-985-1...»,
    это переиздание в двух странах, — поэтому сверяется вхождение, а не
    равенство строки целиком."""
    asked = _digits(isbn)
    if not asked or not title.strip():
        return None
    for row in payload.get("matches", []):
        numbers = {_digits(one) for one in str(row.get("isbn", "")).split(",")}
        if asked in numbers and _same_title(row.get("name", ""), title):
            return int(row["edition_id"])
    return None


def _digits(isbn: str) -> str:
    """ISBN без дефисов и пробелов: пишут его и так, и так."""
    return "".join(one for one in isbn if one.isdigit() or one in "Xx").upper()


def _same_title(found: str, asked: str) -> bool:
    """Название издания против названия тома.

    Не равенство: у издания в названии бывает хвост тома цикла — «Властелин
    Колец. Хранители Кольца» против «Властелин Колец», — а у Google, наоборот,
    подзаголовок. Совпадением считается общее начало: чужая книга общего начала
    не даёт, а издание того же тома даёт всегда."""
    first, second = flattened(found), flattened(asked)
    if not first or not second:
        return False
    return first.startswith(second) or second.startswith(first)
