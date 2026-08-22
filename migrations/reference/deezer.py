"""Соответствия Deezer: номер жанра — наш музыкальный жанр.

Имена наши совпадают с ихними: набор взят у Deezer как есть, решение
пользователя 22.08.2026. Соответствие всё равно записывается, а не выводится
совпадением строк, — метка в базе хранится номером, как у TMDB, и переименуй
Deezer свой жанр, наш останется прежним.

Номера сняты с ручки `/genre` 22.08.2026. `All` (номер 0) в справочник не идёт:
это не жанр, а корзина «всё сразу».
"""

from migrations.reference.rule import Rule

DEEZER = [
    Rule("African Music", "2"),
    Rule("Asian Music", "16"),
    Rule("Brazilian Music", "75"),
    Rule("Indian Music", "81"),
    Rule("Alternative", "85"),
    Rule("Kids", "95"),
    Rule("Classical", "98"),
    Rule("Electro", "106"),
    Rule("Dance", "113"),
    Rule("Rap/Hip Hop", "116"),
    Rule("Jazz", "129"),
    Rule("Pop", "132"),
    Rule("Reggae", "144"),
    Rule("Rock", "152"),
    Rule("Blues", "153"),
    Rule("R&B", "165"),
    Rule("Soul & Funk", "169"),
    Rule("Films/Games", "173"),
    Rule("Latin Music", "197"),
    Rule("Metal", "464"),
    Rule("Folk", "466"),
]
