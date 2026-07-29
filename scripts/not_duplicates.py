"""Вердикты «это не повтор того» и их срок годности.

Проверка повторов читает `docs/not-duplicates.md` вместе с картами и разобранные
пары пропускает — иначе каждый проход разбирал бы одно и то же заново. Строку
пишет человек, отпечатки проставляет сборка карт.

Отпечаток и есть срок годности: изменилось тело любой стороны — вердикт гаснет,
и пара возвращается в разбор. Бессрочный вердикт хуже его отсутствия — он глушит
проверку ровно там, где она однажды сработала.
"""

import re

from project_ast import ROOT, STAMP

VERDICTS = ROOT / "docs/not-duplicates.md"


def verdict_lines() -> list[str]:
    """Строки файла вердиктов. Нет файла — нет и вердиктов."""
    if not VERDICTS.exists():
        return []
    return VERDICTS.read_text(encoding="utf-8").split("\n")


def is_verdict(line: str) -> bool:
    """Вердикт — пункт списка. Объявление, упомянутое в прозе этого файла,
    вердиктом не становится, иначе `--check` краснел бы на пояснении."""
    return line.startswith("- ")


def places(line: str) -> list[tuple[str, str]]:
    """Ссылки строки на объявления и то, что стоит сразу за каждой.

    Ссылка — `путь.py:Класс.метод`. Прочие обратные кавычки в строке это имена
    внутри объяснения, и трогать их нельзя: `Repository._mapped`, упомянутый в
    причине, стороной вердикта не является."""
    tokens = re.findall(r"`([^`]+)`", line)
    return [(token, follows)
            for token, follows in zip(tokens, tokens[1:] + [""])
            if ":" in token and token.partition(":")[0].endswith(".py")]


def stamped(token: str) -> bool:
    return bool(re.fullmatch(f"[0-9a-f]{{{STAMP}}}", token))


def sealed(line: str, index: dict[str, str]) -> str:
    """Строка вердикта с проставленными отпечатками.

    Отпечаток руками не написать, поэтому его ставит сборка — но **только там,
    где его нет**. Разошедшийся не заменяется и не дополняется: заменить его
    значит воскресить вердикт, который проверка уже признала протухшим, и
    сделать это молча, на ровной пересборке карт."""
    for place, follows in places(line):
        if place in index and not stamped(follows):
            line = line.replace(f"`{place}`", f"`{place}` `{index[place]}`", 1)
    return line


def seal(index: dict[str, str]) -> None:
    lines = verdict_lines()
    fresh = [sealed(line, index) if is_verdict(line) else line for line in lines]
    if fresh != lines:
        VERDICTS.write_text("\n".join(fresh), encoding="utf-8")


def malformed(line: str) -> str:
    """Чем строка вердикта негодна. Годная — пусто.

    Вердикт без причины ничего не объясняет следующему, вердикт об одной
    стороне не о чём, а сторона, названная дважды, при каждой сборке получает
    ещё один отпечаток и разрастается."""
    found = [place for place, _ in places(line)]
    if len(found) < 2:
        return "сторон меньше двух"
    if len(set(found)) != len(found):
        return "сторона названа дважды"
    # Причина отделяется тире с пробелами. Искать её после последней обратной
    # кавычки нельзя: в самой причине их сколько угодно.
    if " — " not in line:
        return "нет причины"
    return ""


def expired(lines: list[str], index: dict[str, str]) -> list[str]:
    """Вердикты, которым верить больше нельзя.

    Сторона исчезла — вердикт указывает в пустоту; тело стороны изменилось —
    «это не повтор того» проверялось для другого кода; строка негодна — её
    никто не прочтёт как вердикт. Всё это возвращает пару в разбор."""
    stale = []
    for line in filter(is_verdict, lines):
        wrong = malformed(line)
        if wrong:
            stale.append(f"{line[:60]}… — {wrong}")
            continue
        for place, follows in places(line):
            if place not in index:
                stale.append(f"{place} — такого объявления больше нет")
            elif follows != index[place]:
                stale.append(f"{place} — тело изменилось, разберите пару заново")
    return stale
