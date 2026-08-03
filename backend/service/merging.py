"""Одна игра — одна строка выдачи.

Автоматическая половина дедупликации: то, что склеивается без единой ошибки,
склеивается само и человека не беспокоит. Замер принятого правила — 382 верных
склейки при нуле ложных, 83% из 461 верной пары на 224 запросах, 03.08.2026.

Что не склеилось, остаётся на глазах человека: он убирает лишнее руками, и это
помнит `RemovedRepository`.
"""

from backend.model import Kind, SearchHit, Source
from backend.service.titles import flattened, without_edition

# Слова сборника. Сборник — не издание: это несколько игр под одной строкой, и
# показывать его в выдаче незачем. Решение пользователя 03.08.2026.
SETS = ("bundle", "collection", "trilogy", "anthology", "антология",
        "коллекция", "compilation")

# Чем ближе к началу, тем охотнее показываем. Это решение пользователя, а не
# замер: «победитель — по приоритету steam > gog > old-games».
PRIORITY = (Source.STEAM, Source.GOG, Source.OLD_GAMES)


def _a_set(hit: SearchHit) -> bool:
    return any(word in hit.title.lower() for word in SETS)


def _asked_for(hit: SearchHit, asked: list[str]) -> bool:
    """Тот ли это сборник, который спросили.

    Сравниваются слова, а не строка целиком: человек набирает «mortal kombat
    trilogy», а называется она «Mortal Kombat Trilogy» — совпадёт, — но выдача
    того же запроса принесёт и «SUPERHOT ONE OF US BUNDLE», и она не должна
    показаться.

    Приведение здесь без снятия хвоста: слово сборника само из издательских, и
    `without_edition` срезало бы ровно то, по чему идёт сравнение."""
    return bool(asked) and set(asked) <= set(flattened(hit.title).split())


def _keys(hit: SearchHit, *, alone: bool) -> set[str]:
    """Чем строка узнаётся. Внутри одного источника ключ только один —
    показываемое название.

    Замерено 03.08.2026: со вторым названием склеек внутри магазина становится
    126 вместо 51, и склеиваются ими разные игры одной серии — `Worms` с
    `Worms 2`, `Space Quest I` со `Space Quest II`. Между источниками этого не
    случается, поэтому там добавочные ключи разрешены."""
    keys = {without_edition(hit.title)}
    if not alone:
        keys.add(without_edition(hit.original_title))
        keys.update(without_edition(one) for one in hit.aliases)
    return {one for one in keys if one}


def _dressed(hit: SearchHit) -> bool:
    """Несёт ли название слова издания. Внутри источника приоритет не различает
    — источник один, — и побеждает строка без них: «Fallout 3» вернее, чем
    «Fallout 3 - Game of the Year Edition»."""
    return flattened(hit.title) != without_edition(hit.title)


def _rank(hit: SearchHit) -> tuple:
    """Порядок выбора победителя. Хвост — короче название, меньше
    идентификатор — не смысл, а устойчивость: без него выбор зависел бы от
    порядка ответов сети."""
    return (PRIORITY.index(hit.source) if hit.source in PRIORITY else len(PRIORITY),
            _dressed(hit), len(hit.title), hit.source_id)


class _Groups:
    """Строки, слитые в группы, со счётом состава по источникам.

    Состав держится не для порядка. Объединение транзитивно, а замеренное
    правило попарно, и без проверки состава третья строка протаскивает внутрь
    источника склейку, которую правило 4 запрещает: `Steam «Worms»` плюс две
    строки old-games с общим вторым названием дают одну группу, и «Worms 2»
    исчезает."""

    def __init__(self, primary: list[str], sources: list[Source]) -> None:
        self._of = list(range(len(primary)))
        self._primary = primary
        self._sources = sources
        self._members = {number: [number] for number in range(len(primary))}

    def head(self, one: int) -> int:
        while self._of[one] != one:
            one = self._of[one]
        return one

    def _shown(self, head: int) -> dict[Source, set[str]]:
        """Показываемые названия группы, разложенные по источникам."""
        found: dict[Source, set[str]] = {}
        for number in self._members[head]:
            found.setdefault(self._sources[number], set()).add(
                self._primary[number])
        return found

    def _joinable(self, one: int, other: int) -> bool:
        """Нельзя, если у какого-то источника в обеих группах лежат строки с
        разными показываемыми названиями: внутри источника ключ только один, и
        такая склейка означала бы, что `Worms` и `Worms 2` — одна игра."""
        mine, theirs = self._shown(one), self._shown(other)
        return all(mine[source] == theirs[source]
                   for source in mine.keys() & theirs.keys())

    def join(self, one: int, other: int) -> None:
        first, second = self.head(one), self.head(other)
        if first == second or not self._joinable(first, second):
            return
        self._of[second] = first
        self._members[first].extend(self._members.pop(second))


def _grouped(flat: list[SearchHit]) -> list[int]:
    """Номер группы для каждой строки, сквозной по всем выдачам.

    Два прохода, как и правило: сперва внутри источника по одному ключу, потом
    между источниками по любому. Второй проход сверяет строку со **всеми**
    занявшими её ключ, а не с первой попавшейся: с одной первой законная
    склейка терялась бы в зависимости от порядка ответов сети."""
    groups = _Groups([without_edition(one.title) for one in flat],
                     [one.source for one in flat])

    inside: dict[tuple[Source, str], list[int]] = {}
    for number, hit in enumerate(flat):
        for key in _keys(hit, alone=True):
            seen = inside.setdefault((hit.source, key), [])
            for other in seen:
                groups.join(other, number)
            seen.append(number)

    between: dict[str, list[int]] = {}
    for number, hit in enumerate(flat):
        for key in _keys(hit, alone=False):
            seen = between.setdefault(key, [])
            for other in seen:
                if flat[other].source is not hit.source:
                    groups.join(other, number)
            seen.append(number)

    return [groups.head(number) for number in range(len(flat))]


def merged(answers: list[list[SearchHit]], query: str) -> list[list[SearchHit]]:
    """Выдачи, из которых убрано лишнее: сборники и проигравшие строки.

    Порядок внутри каждой выдачи сохраняется — его задал источник, а
    переплетают выдачи после. Победитель уходит целиком: поля не смешиваются,
    проигравшая строка исчезает вся.

    Строка поиска нужна ради одного исключения: остаётся **тот** сборник,
    который спросили. Набравший «Mortal Kombat Trilogy» обязан её найти — но
    посторонние сборники из той же выдачи ему не нужны, а они там бывают.

    **Склейка работает только на играх, и это не перестраховка.** Замер делался
    на игровых строках, а решение — про одну игру в двух-трёх магазинах. У кино
    источник один, склеивать нечего, зато два разных фильма с одним названием —
    обычное дело: «Дюна» 1984 года и «Дюна» 2021-го, и по общему правилу они
    слились бы в одну строку. Смешанной выдачи у проекта не бывает — вкладка
    первичный фильтр, — так что проверка стоит на всём наборе разом."""
    if not all(one.kind is Kind.GAME for answer in answers for one in answer):
        return answers

    asked = flattened(query).split()
    # Слово сборника обязано стоять в самом запросе: без этой половины «fallout»
    # оставлял бы «Fallout Classic Collection» — слова запроса в её названии
    # есть, а сборника человек не просил.
    named = any(word in asked for word in SETS)
    kept = [[one for one in answer
             if not _a_set(one) or (named and _asked_for(one, asked))]
            for answer in answers]

    flat = [one for answer in kept for one in answer]
    heads = _grouped(flat)
    winners: dict[int, SearchHit] = {}
    for number, hit in enumerate(flat):
        group = heads[number]
        if group not in winners or _rank(hit) < _rank(winners[group]):
            winners[group] = hit

    survivors = {id(one) for one in winners.values()}
    return [[one for one in answer if id(one) in survivors] for answer in kept]
