"""Что ответила чужая база и как её выдача складывается со своей.

Лежит в модели, а не в сервисе поиска, по двум причинам: складывать приходится и
клиенту — своё он уже показал, внешнее приехало потом, — а сам ответ едет через
границу слоёв, где разрешены только типы `backend/model/`."""

from dataclasses import dataclass

from backend.model.kinds import Source
from backend.model.outcome import Refusal
from backend.model.view import CardView


@dataclass(frozen=True, slots=True)
class ExternalSearch:
    """Отказ — поле в результате, а не исключение: у границы потоков второго
    канала доставки нет."""

    views: tuple[CardView, ...]
    refusals: tuple[Refusal, ...]


def merge_results(local: list[CardView],
                  external: list[CardView]) -> list[CardView]:
    """Сначала своё целиком, потом чужое. Правило одно на всю выдачу поиска —
    и на строку ввода, и на клик по человеку.

    Порядок внутри половин не трогается: своя приходит уже упорядоченной, у
    чужой порядок задан источником — у него есть данные о популярности и
    совпадении с запросом, которых у нас нет.

    Дубли снимаются по паре «источник + идентификатор»: совпавшее чужое не
    показывается вторым разом, потому что своё уже показано выше и у него есть
    оценка, теги и закладка. Одна и та же игра из Steam и из GOG под эту пару
    не попадает и показывается дважды."""
    merged = list(local)
    seen: set[tuple[Source, str]] = {(view.source, view.source_id)
                                     for view in local}
    for view in external:
        key = (view.source, view.source_id)
        if key in seen:
            continue
        seen.add(key)
        merged.append(view)
    return merged
