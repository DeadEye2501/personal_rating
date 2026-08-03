"""Каждый вызов, который мост делает бэкенду, обязан ему подходить.

Записывающий двойник принимает любое имя с любыми доводами — переименованный
метод и лишний довод прошли бы молча на всём наборе. Этой проверкой закрывается
ровно та дыра, и закрывается она **обеими половинами**: имя должно
существовать, а доводы — сходиться с сигнатурой. Половины имён мало: верное имя
с лишним доводом — это верное имя и неверный вызов, и до живого запуска его не
видит никто.

Вызовы собираются разбором исходников, а не переписываются сюда руками: список,
набранный вручную, разошёлся бы с кодом молча — и это была бы та же дыра, только
на этаж выше."""

import ast
import inspect
from pathlib import Path

import pytest

from backend.app import Backend
from bridge.api import Api
from bridge.refs import DOMAINS as ENTITY_DOMAINS

ROOT = Path(__file__).resolve().parents[2]
SOURCES = sorted((ROOT / "bridge").glob("*.py"))

DOMAINS = {"library", "marks", "refs", "feed", "search", "world", "covers"}

# Справочник людей и студий зовётся через посредника: имя домена приходит
# доводом, и корень цепочки — вызов, а не `back`. Такие места разворачиваются в
# оба домена, а список берётся у самого моста, чтобы не объявлять его дважды.
CHOOSER = "_of"


def chain(node):
    """`back.tags.create(...)` → `[("tags", "create")]`.

    У выбора справочника корень — `_of(back, domain)`, и раскрывается он в оба
    домена сразу: иначе четыре обращения к людям и студиям остались бы вне
    проверки, а именно там двойник и принимает любое имя."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    parts.reverse()
    if isinstance(node, ast.Name) and node.id == "back":
        return [tuple(parts)]
    if _chooses(node):
        return [(domain, *parts) for domain in ENTITY_DOMAINS]
    return []


def _chooses(node) -> bool:
    return (isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name) and node.func.id == CHOOSER
            and any(isinstance(one, ast.Name) and one.id == "back"
                    for one in node.args))


def calls() -> dict[str, dict[str, tuple]]:
    """Что мост зовёт у бэкенда: путь, число позиционных доводов и имена
    названных. Доводы считаются, а не только имена: расхождение сигнатуры — тот
    род поломки, которого `hasattr` не видит вовсе."""
    found = {}
    for path in SOURCES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            for parts in chain(node.func):
                named = tuple(word.arg for word in node.keywords)
                found.setdefault(path.name, {})[".".join(parts)] = (
                    len(node.args), named)
    return found


def fields_read() -> set[str]:
    """Что мост читает у бэкенда полем, а не зовёт.

    Собирается отдельно от вызовов: у поля нет скобок, и `calls()` его не видит
    вовсе — переименуй `Backend.scale`, и весь набор останется зелёным, а окно
    ответит «непредвиденный сбой» на первый же вопрос страницы."""
    found = set()
    for path in SOURCES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        called = {node.func for node in ast.walk(tree)
                  if isinstance(node, ast.Call)}
        found.update(
            node.attr for node in ast.walk(tree)
            if isinstance(node, ast.Attribute) and node not in called
            and isinstance(node.value, ast.Name) and node.value.id == "back")
    return found


@pytest.mark.parametrize("name", sorted(fields_read()))
def test_every_field_the_bridge_reads_exists_on_the_backend(name):
    assert hasattr(Backend, name), f"у бэкенда нет поля {name}"


def test_the_guard_sees_the_fields_the_bridge_reads():
    """Порога «собралось хотя бы что-то» мало и здесь: собери разбор ноль имён —
    и проверка выше стала бы пустым перебором, зелёным при любом расхождении."""
    assert "scale" in fields_read()


def flat() -> list[tuple]:
    return sorted((path, count, named)
                  for calls_of in calls().values()
                  for path, (count, named) in calls_of.items())


def surface(api) -> set[str]:
    """Поверхность моста так же, как её собирает pywebview: `dir()` без имён с
    подчёркиванием, с рекурсией в не-вызываемые объекты."""
    found = set()
    for name in dir(api):
        if name.startswith("_"):
            continue
        value = getattr(api, name)
        if callable(value):
            found.add(name)
        else:
            found.update(f"{name}.{inner}" for inner in surface(value))
    return found


def test_the_bridge_shows_seven_domains_and_cancelling(spy):
    """Семь доменов, а не шесть: поиск отделён от ленты — описать их одной
    фразой без «и» нельзя."""
    shown = surface(Api(spy))

    assert {name.split(".")[0] for name in shown} == DOMAINS | {"cancel"}


def test_each_name_hides_its_own_domain(spy):
    """Имя на поверхности проверяется отдельно от того, что за ним стоит:
    `self.search = Marks(thread)` прошло бы молча, и страница звала бы теги
    вместо поиска. Тот же род поломки, что перепутанные люди со студиями."""
    api = Api(spy)

    behind = {name: type(getattr(api, name)).__name__ for name in DOMAINS}

    assert behind == {"library": "Library", "marks": "Marks", "refs": "Refs",
                      "feed": "FeedBridge", "search": "Search",
                      "world": "World", "covers": "Covers"}


def test_cancelling_reaches_the_thread(spy):
    """Отмена — не заглушка: без неё устаревшие ответы доезжают до страницы, а
    брошенные запросы досиживают свой срок, тратя квоту источника."""
    gone = []
    spy.cancel = gone.append

    assert Api(spy).cancel([4, 5]) == {"ok": None}
    assert gone == [[4, 5]]


def test_cancelling_something_that_is_not_a_list_is_answered(spy):
    """`ops` приходит из JSON: чем бы он ни оказался, наружу уходит ответ, а не
    исключение — третьего вида у моста нет."""
    assert Api(spy).cancel(7)["fail"] == "broken"


@pytest.mark.parametrize("domain", sorted(DOMAINS))
def test_every_domain_gives_the_guard_something_to_check(domain):
    """Порога «собралось хотя бы что-то» мало: переименуй довод `back` в одном
    файле — и весь его домен молча уйдёт из-под проверки, а общее число едва
    дрогнет. Замерено: так уходят четыре домена из семи."""
    assert calls().get(f"{domain}.py"), f"из {domain}.py не собрано ни вызова"


@pytest.mark.parametrize(("path", "count", "named"), flat())
def test_every_call_the_bridge_makes_fits_the_backend(path, count, named):
    where = Backend
    for step in path.split("."):
        assert hasattr(where, step), f"{path}: нет {step}"
        where = _behind(where, step)

    # `bind` проверяет не только число, но и обязательные без умолчания: вызов
    # без `kind` у метода, который его требует, покраснеет здесь, а не в окне.
    # Названные доводы идут по именам — опечатка в `overwrite` иначе молчит.
    inspect.signature(where).bind(None, *range(count),
                                  **dict.fromkeys(named))


def _behind(where, step):
    """У `Backend` поля объявлены аннотациями, и значения у класса нет — за
    именем стоит тип из `__annotations__`. У сервисов и репозиториев дальше идут
    обычные методы класса."""
    annotations = getattr(where, "__annotations__", {})
    return annotations.get(step) or getattr(where, step)


def test_every_domain_on_the_surface_actually_reaches_the_backend(spy, asked):
    """Поверхность проверяется отдельно от того, что за ней работает: `Api` с
    доменом на пустом потоке даёт «непредвиденный сбой» на каждый вызов, а имена
    при этом на месте. Тот же класс, что несобранный загрузчик в бэкенде —
    девятьсот тестов зелёные, приложение не работает."""
    answers, log = asked
    answers.update({"library.unlink": None, "wishlist.remove": None,
                    "genres.list_for_kind": [], "feed.views_of": [],
                    "search.local": [], "series.refresh": None,
                    "posters.has": True})
    api = Api(spy)

    api.library.unlink(1)
    api.marks.unwish(1)
    api.refs.genres("film")
    api.feed.views_of(1, [1])
    api.search.local(1, "movie", "одиссея")
    api.world.refresh_series(1, 1)
    api.covers.has(1)

    assert [name for name, _, _ in log] == [
        "library.unlink", "wishlist.remove", "genres.list_for_kind",
        "feed.views_of", "search.local", "series.refresh", "posters.has"]
