"""Одна игра — одна строка выдачи.

Автоматическая половина дедупликации: то, что склеивается без единой ошибки,
склеивается само и человека не беспокоит. Замер боевой реализации на
независимой разметке — 383 верных склейки при нуле ложных, 83% из 461 верной
пары на 224 запросах, 03.08.2026. Английское название GOG в ключи не берётся
по решению пользователя, и стоит это ровно одну пару — «Ведьмака 2».

Что не склеилось, остаётся на глазах человека: он убирает лишнее руками, и это
помнит `RemovedRepository`.
"""

from dataclasses import replace

from backend.language import in_latin, in_russian
from backend.model import Kind, SearchHit, Source
from backend.service.titles import flattened, without_edition
from backend.unique import unique

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


def _keys(hit: SearchHit, *, alone: bool) -> list[str]:
    """Чем строка узнаётся. Внутри одного источника ключ только один —
    показываемое название.

    Замерено 03.08.2026: со вторым названием склеек внутри магазина становится
    126 вместо 51, и склеиваются ими разные игры одной серии — `Worms` с
    `Worms 2`, `Space Quest I` со `Space Quest II`. Между источниками этого не
    случается, поэтому там добавочные ключи разрешены.

    Список, а не множество, и порядок в нём — правило: **своё показываемое
    название сильнее псевдонима.** Строка примыкает к группе первым подошедшим
    ключом, а `_joinable` вторую склейку уже запретит, так что очередь решает
    исход. Множество отдавало эту очередь хешам, а хеш строки солится на запуск
    процесса: замерено 03.08.2026 — девять солей из шестнадцати показывали
    дубль `Worms`, семь верную пару, при зелёном наборе на любой."""
    keys = [without_edition(hit.title)]
    if not alone:
        keys.append(without_edition(hit.original_title))
        keys.extend(without_edition(one) for one in hit.aliases)
    return unique(one for one in keys if one)


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


def _other_name(winner: SearchHit, group: list[SearchHit]) -> str:
    """Имя на другой письменности, взятое из группы.

    Одно из двух полей, которыми проигравшая строка делится с победителем —
    второе год, — и исключение это принято решением пользователя 03.08.2026. Собирается именно
    здесь, до того как проигравшие исчезнут: группа склейки — единственное
    место, где два имени **доказанно** про одну игру, их свело правило, а не
    догадка.

    Показываемое имя не трогается: список выдачи от этого не меняется, а второе
    поле у кандидатов из магазинов и так пустое — Steam и GOG в выдаче отдают по
    одному имени.

    Своё второе имя стоит первым в списке и потому сильнее чужого: у old-games
    оно со страницы той же игры. Оно же и ответ, когда другой письменности в
    группе не нашлось: `Dune II: The Building of a Dynasty` знает про себя
    `Dune II: Battle for Arrakis`, письменность у них одна, и затирать его
    пустотой не за что.

    Чужие имена перебираются тем же ключом, каким выбран победитель, а не в
    порядке выдач: внутри одного источника порядок задаёт сам источник, и без
    сортировки второе имя доставалось бы от строки-издания — «Готика II . Gold»
    вместо «Готика II», если old-games вернёт издание первым."""
    wanted = in_latin if in_russian(winner.title) else in_russian
    names = [winner.original_title,
             *(name for one in sorted(group, key=_rank) if one is not winner
               for name in (one.title, one.original_title))]
    return next((one for one in names if one and wanted(one)),
                winner.original_title)


def _earliest_year(group: list[SearchHit]) -> int | None:
    """Самый ранний год группы: игра не могла выйти раньше самой себя, значит из
    разошедшихся дат верна ранняя. Решение пользователя 03.08.2026.

    Правило бьёт и по самому победителю: Steam помечает игру годом появления в
    магазине, и он всегда позже настоящего — `Arcanum` 2016 против 2001. В
    выдаче Steam года не отдаёт вовсе, и без этого правила «Fallout 2»
    показывался бы без года, хотя два соседа по группе знали 1998-й.

    Чем правило рискует: мусорной ранней датой. Риск принят пользователем —
    правится руками через окно карточки."""
    years = [one.year for one in group if one.year]
    return min(years) if years else None


def _completed(winner: SearchHit, group: list[SearchHit]) -> SearchHit:
    """Победитель, добравший из группы то, чего у него нет."""
    return replace(winner, original_title=_other_name(winner, group),
                   year=_earliest_year(group))



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


def _without_sets(answers: list[list[SearchHit]],
                  query: str) -> list[list[SearchHit]]:
    """Выдачи без сборников — кроме того, который спросили прямо.

    Слово сборника обязано стоять в самом запросе: без этой половины «fallout»
    оставлял бы «Fallout Classic Collection» — слова запроса в её названии
    есть, а сборника человек не просил."""
    asked = flattened(query).split()
    named = any(word in asked for word in SETS)
    return [[one for one in answer
             if not _a_set(one) or (named and _asked_for(one, asked))]
            for answer in answers]


def merged(answers: list[list[SearchHit]], query: str) -> list[list[SearchHit]]:
    """Выдачи, из которых убрано лишнее: сборники и проигравшие строки.

    Порядок внутри каждой выдачи сохраняется — его задал источник, а
    переплетают выдачи после. Победитель уходит целиком, и проигравшая строка
    исчезает вся — **кроме имени на другой письменности и года выхода**: их
    победитель забирает себе. Оба исключения приняты решением пользователя
    03.08.2026 и других нет. Подробности у `_completed`.

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

    kept = _without_sets(answers, query)

    flat = [one for answer in kept for one in answer]
    heads = _grouped(flat)
    groups: dict[int, list[SearchHit]] = {}
    for number, hit in enumerate(flat):
        groups.setdefault(heads[number], []).append(hit)

    winners = {}
    for rows in groups.values():
        winner = min(rows, key=_rank)
        winners[id(winner)] = _completed(winner, rows)
    return [[winners[id(one)] for one in answer if id(one) in winners]
            for answer in kept]
